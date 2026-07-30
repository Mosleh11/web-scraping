"""TD 4.1 - Empreinte technique d'un domaine (OSINT passif).

Sources : WHOIS (registre public), headers HTTP, certificat TLS presente par le
serveur, sitemap.xml, robots.txt. Toutes publiques, aucune authentification.

Usage :
    python td41_domaine.py wikipedia.org
    python td41_domaine.py ipssi.net --sortie rapport_ipssi.json
    python td41_domaine.py exemple.fr --crtsh      # voir l'avertissement robots
"""

import argparse
import json
import re
import socket
import ssl
import time
import xml.etree.ElementTree as ET

import requests
import whois
from protego import Protego

HEADERS = {"User-Agent": "IPSSI-OSINT (+cours@ipssi.fr)"}
DELAI = 1.0  # politesse : >= 1 s entre requetes

# Motifs revelateurs d'un environnement qui n'est pas la production.
MOTIFS_SENSIBLES = [
    "preprod", "staging", "recette", "dev", "test", "uat", "sandbox",
    "demo", "qa", "admin", "vpn", "mail", "ftp", "git", "jenkins",
]


def robots_autorise(url: str, agent: str = HEADERS["User-Agent"]) -> bool:
    """Verifie robots.txt AVANT de requeter, comme l'exige la regle 4 du TP."""
    base = "/".join(url.split("/")[:3])
    try:
        r = requests.get(f"{base}/robots.txt", headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return True  # pas de robots.txt publie = pas de restriction
        return Protego.parse(r.text).can_fetch(url, agent)
    except requests.RequestException:
        return True


def analyse_whois(domaine: str) -> dict:
    """Registre public : titulaire technique, dates, serveurs de noms."""
    try:
        w = whois.whois(domaine)
        return {
            "registrar": str(w.registrar or "n/a"),
            "creation_date": str(w.creation_date or "n/a")[:10],
            "expiration_date": str(w.expiration_date or "n/a")[:10],
            # pas de champ nominatif (nom, email, telephone du titulaire) :
            # ce sont des donnees personnelles au sens du RGPD
            "name_servers": sorted({str(n).lower() for n in (w.name_servers or [])}),
            "country": str(w.country or "n/a"),
        }
    except Exception as e:
        return {"erreur": f"{type(e).__name__}: {e}"}


def analyse_tls(domaine: str) -> dict:
    """Valide le certificat, puis le relit sans verification s'il est refuse.

    Un certificat invalide est en soi un resultat : le site reste joignable,
    mais aucun visiteur n'a de garantie d'authenticite.
    """
    for hote in (domaine, f"www.{domaine}"):
        try:
            with socket.create_connection((hote, 443), timeout=10) as sock:
                with ssl.create_default_context().wrap_socket(
                    sock, server_hostname=hote
                ) as tls:
                    cert = tls.getpeercert()
            return {
                "hote_teste": hote,
                "certificat_valide": True,
                "expire_le": cert.get("notAfter", "n/a"),
                "emetteur": next(
                    (v for bloc in cert.get("issuer", ()) for k, v in bloc
                     if k == "organizationName"), "n/a"),
            }
        except ssl.SSLCertVerificationError as e:
            permissif = ssl.create_default_context()
            permissif.check_hostname = False
            permissif.verify_mode = ssl.CERT_NONE
            try:
                with socket.create_connection((hote, 443), timeout=10) as sock:
                    with permissif.wrap_socket(sock, server_hostname=hote) as tls:
                        cert = tls.getpeercert(binary_form=False) or {}
                return {
                    "hote_teste": hote,
                    "certificat_valide": False,
                    "erreur_validation": e.verify_message or str(e)[:120],
                }
            except OSError:
                continue
        except OSError:
            continue
    return {"certificat_valide": None, "erreur_validation": "port 443 injoignable"}


def analyse_headers(domaine: str) -> dict:
    """En-tetes de reponse : serveur, technologies, en-tetes de securite.

    Repli en clair si HTTPS echoue : un site qui ne repond qu'en HTTP est un
    constat a documenter, pas une erreur a masquer.
    """
    schemas = [f"https://{domaine}", f"http://{domaine}"]
    r = None
    for url in schemas:
        try:
            r = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
            break
        except requests.RequestException as e:
            derniere = f"{type(e).__name__}"
    if r is None:
        return {"erreur": derniere}

    try:
        h = r.headers
        securite = {
            "csp": "Content-Security-Policy" in h,
            "hsts": "Strict-Transport-Security" in h,
            "x_frame_options": h.get("X-Frame-Options", "absent"),
            "x_content_type_options": h.get("X-Content-Type-Options", "absent"),
            "referrer_policy": h.get("Referrer-Policy", "absent"),
        }
        manquants = [c for c, v in securite.items() if v is False or v == "absent"]
        return {
            "status": r.status_code,
            "url_finale": r.url,
            "https_fonctionnel": r.url.startswith("https://"),
            "server": h.get("Server", "non divulgue"),
            "x_powered_by": h.get("X-Powered-By", "non divulgue"),
            "securite": securite,
            "entetes_securite_manquants": manquants,
        }
    except requests.RequestException as e:
        return {"erreur": f"{type(e).__name__}: {e}"}


def sous_domaines_certificat(domaine: str) -> list[str]:
    """Noms couverts par le certificat TLS que le serveur presente lui-meme.

    Remplace crt.sh (voir --crtsh) : l'information vient du serveur cible
    pendant la poignee de main TLS, exactement comme pour un navigateur.
    Aucun tiers interroge, aucun robots.txt en jeu.
    """
    for hote in (f"www.{domaine}", domaine):
        try:
            contexte = ssl.create_default_context()
            with socket.create_connection((hote, 443), timeout=10) as sock:
                with contexte.wrap_socket(sock, server_hostname=hote) as tls:
                    cert = tls.getpeercert()
            return sorted({v for k, v in cert.get("subjectAltName", ()) if k == "DNS"})
        except (OSError, ssl.SSLError):
            continue
    return []


def sous_domaines_sitemap(domaine: str) -> list[str]:
    """Hotes reellement publies par le site dans son propre sitemap."""
    hotes = set()
    candidats = (f"https://{domaine}/sitemap.xml", f"https://www.{domaine}/sitemap.xml",
                 f"http://{domaine}/sitemap.xml")
    for url in candidats:
        if not robots_autorise(url):
            continue
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                continue
            racine = ET.fromstring(r.content)
            for loc in racine.iter():
                if loc.tag.endswith("loc") and loc.text:
                    hote = loc.text.split("/")[2] if "//" in loc.text else ""
                    if hote.endswith(domaine):
                        hotes.add(hote.lower())
            break
        except (requests.RequestException, ET.ParseError):
            continue
    return sorted(hotes)


def sous_domaines_crtsh(domaine: str) -> dict:
    """Version de l'enonce, desactivee par defaut.

    crt.sh publie 'User-agent: * / Disallow: /' : interroger son API contredit
    la regle 4 du TP ("robots.txt respecte pour chaque cible"). La fonction
    verifie donc robots.txt et refuse par defaut.
    """
    url = f"https://crt.sh/?q=%.{domaine}&output=json"
    if not robots_autorise(url):
        return {
            "statut": "refuse",
            "raison": "crt.sh interdit tout crawl via robots.txt (Disallow: /)",
            "sous_domaines": [],
        }
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        noms = {
            e["name_value"]
            for e in r.json()
            if "*" not in e["name_value"] and e["name_value"].endswith(domaine)
        }
        return {"statut": "ok", "sous_domaines": sorted(noms)[:100]}
    except Exception as e:
        return {"statut": "erreur", "raison": str(e), "sous_domaines": []}


def analyse_robots(domaine: str) -> dict:
    # meme repli qu'ailleurs : un site sans HTTPS valide a quand meme un robots
    r = None
    for schema in ("https", "http"):
        try:
            r = requests.get(f"{schema}://{domaine}/robots.txt", headers=HEADERS,
                             timeout=10)
            break
        except requests.RequestException as e:
            derniere = type(e).__name__
    if r is None:
        return {"statut": derniere, "extrait": ""}
    try:
        if r.status_code != 200:
            return {"statut": f"HTTP {r.status_code}", "extrait": ""}
        lignes = r.text.splitlines()
        return {
            "statut": "200",
            "nb_lignes": len(lignes),
            "sitemaps": [l.split(":", 1)[1].strip() for l in lignes
                         if l.lower().startswith("sitemap:")],
            "nb_disallow": sum(1 for l in lignes if l.lower().startswith("disallow:")),
            "extrait": r.text[:600],
        }
    except requests.RequestException as e:
        return {"statut": f"{type(e).__name__}", "extrait": ""}


def classer_sous_domaines(sous_domaines: list[str]) -> dict:
    """Repere les hotes qui trahissent un environnement hors production."""
    sensibles = [
        s for s in sous_domaines
        if any(re.search(rf"(^|[.\-]){m}([.\-]|$)", s) for m in MOTIFS_SENSIBLES)
    ]
    return {
        "total": len(sous_domaines),
        "wildcards": [s for s in sous_domaines if s.startswith("*")],
        "potentiellement_sensibles": sensibles,
    }


def analyser_domaine(domaine: str, avec_crtsh: bool = False) -> dict:
    print(f"[*] Analyse de {domaine}")

    try:
        ip = socket.gethostbyname(domaine)
    except OSError as e:
        ip = f"resolution impossible ({type(e).__name__})"

    rapport = {"domaine": domaine, "ip": ip}

    rapport["whois"] = analyse_whois(domaine)
    time.sleep(DELAI)

    rapport["headers_http"] = analyse_headers(domaine)
    time.sleep(DELAI)

    rapport["tls"] = analyse_tls(domaine)
    time.sleep(DELAI)

    certificat = sous_domaines_certificat(domaine)
    time.sleep(DELAI)
    sitemap = sous_domaines_sitemap(domaine)
    time.sleep(DELAI)

    rapport["sous_domaines"] = {
        "certificat_tls": certificat,
        "sitemap": sitemap,
        "crtsh": sous_domaines_crtsh(domaine) if avec_crtsh
        else {"statut": "non interroge", "raison": "robots.txt de crt.sh interdit "
              "tout crawl ; relancer avec --crtsh pour forcer", "sous_domaines": []},
    }

    connus = sorted(set(certificat) | set(sitemap)
                    | set(rapport["sous_domaines"]["crtsh"]["sous_domaines"]))
    rapport["synthese_sous_domaines"] = classer_sous_domaines(connus)
    rapport["robots_txt"] = analyse_robots(domaine)
    return rapport


def main():
    p = argparse.ArgumentParser(description="Empreinte technique d'un domaine")
    p.add_argument("domaine", nargs="?", default="wikipedia.org")
    p.add_argument("--sortie", default=None)
    p.add_argument("--crtsh", action="store_true",
                   help="interroge crt.sh malgre son robots.txt (deconseille)")
    args = p.parse_args()

    rapport = analyser_domaine(args.domaine, avec_crtsh=args.crtsh)
    sortie = args.sortie or f"rapport_domaine_{args.domaine.replace('.', '_')}.json"
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)

    synthese = rapport["synthese_sous_domaines"]
    entetes = rapport["headers_http"]
    print(f"[+] Rapport : {sortie}")
    print(f"    IP              : {rapport['ip']}")
    print(f"    Serveur         : {entetes.get('server', 'n/a')}")
    print(f"    HTTPS valide    : {rapport['tls'].get('certificat_valide')}")
    print(f"    Sous-domaines   : {synthese['total']}")
    print(f"    Dont sensibles  : {len(synthese['potentiellement_sensibles'])}")
    print(f"    Entetes manquants : {', '.join(entetes.get('entetes_securite_manquants', [])) or 'aucun'}")


if __name__ == "__main__":
    main()
