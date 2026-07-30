"""TD 4.2 - Fiche de renseignement sur une entite publique.

Trois sources publiques croisees :
  1. registre SIRENE (API ouverte de l'Etat, sans cle)
  2. Wikipedia (infobox + introduction)
  3. veille presse par flux RSS

Usage :
    python td42_entite.py TotalEnergies
    python td42_entite.py "BNP Paribas" --sortie fiche_bnp.json
"""

import argparse
import json
import re
import time
import unicodedata

import feedparser
import requests
from bs4 import BeautifulSoup
from protego import Protego

HEADERS = {"User-Agent": "IPSSI-OSINT (+cours@ipssi.fr)"}
DELAI = 1.0

# L'URL de l'enonce (api.annuaire-entreprises.data.gouv.fr) ne resout plus.
# L'API officielle en service est recherche-entreprises.api.gouv.fr.
API_SIRENE = "https://recherche-entreprises.api.gouv.fr/search"

# Google News interdit /rss/search dans son robots.txt : on passe par Bing News,
# dont le robots.txt autorise /news/search (verifie dans robots_autorise).
FLUX_PRESSE = "https://www.bing.com/news/search?q={q}&format=RSS&setmkt=fr-FR"


def robots_autorise(url: str, agent: str = HEADERS["User-Agent"]) -> bool:
    base = "/".join(url.split("/")[:3])
    try:
        r = requests.get(f"{base}/robots.txt", headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return True
        return Protego.parse(r.text).can_fetch(url, agent)
    except requests.RequestException:
        return True


# Formes juridiques usuelles a tolerer quand on compare un nom d'usage au
# nom legal : "TotalEnergies" vs "TOTALENERGIES SE".
SUFFIXES_LEGAUX = ("", "se", "sa", "sas", "sasu", "sarl", "sca", "snc")


def _normaliser(texte: str) -> str:
    # l'API accole parfois un alias : "TOTALENERGIES SE (TOTALENERGIE SE)"
    sans_alias = re.sub(r"\(.*?\)", "", texte or "")
    sans_accents = unicodedata.normalize("NFKD", sans_alias).encode("ascii", "ignore")
    return re.sub(r"[^a-z0-9]", "", sans_accents.decode().lower())


def _meilleure_correspondance(nom: str, resultats: list[dict]) -> tuple[dict, bool]:
    """Un groupe a des dizaines d'entites : results[0] est souvent une filiale.

    On privilegie l'entite dont la denomination legale correspond au nom
    recherche, eventuellement suivi d'une forme juridique.
    """
    cible = _normaliser(nom)
    attendus = {cible + s for s in SUFFIXES_LEGAUX}
    for ent in resultats:
        if _normaliser(ent.get("nom_complet", "")) in attendus:
            return ent, True
    return resultats[0], False


def chercher_sirene(nom: str) -> dict:
    """Registre SIRENE : donnees d'immatriculation, publiques par construction."""
    resultats, total = [], 0
    try:
        # l'API pagine par 10 : la maison mere d'un groupe n'est pas toujours
        # en page 1 (TOTALENERGIES SE arrive en page 2 derriere ses filiales)
        for page in (1, 2, 3):
            r = requests.get(API_SIRENE,
                             params={"q": nom, "limite": 10, "page": page},
                             headers=HEADERS, timeout=15)
            r.raise_for_status()
            donnees = r.json()
            total = donnees.get("total_results", 0)
            lot = donnees.get("results", [])
            resultats.extend(lot)
            if not lot or any(_normaliser(e.get("nom_complet", "")) in
                              {_normaliser(nom) + s for s in SUFFIXES_LEGAUX}
                              for e in lot):
                break
            time.sleep(DELAI)

        if not resultats:
            return {"resultat": "aucune correspondance dans SIRENE"}

        ent, exacte = _meilleure_correspondance(nom, resultats)
        siege = ent.get("siege") or {}
        return {
            "siren": ent.get("siren"),
            "denomination": ent.get("nom_complet"),
            "adresse_siege": siege.get("adresse"),
            "code_naf": ent.get("activite_principale"),
            "date_creation": ent.get("date_creation"),
            "tranche_effectif": ent.get("tranche_effectif_salarie"),
            "nature_juridique": ent.get("nature_juridique"),
            "correspondance_exacte": exacte,
            # l'API classe par pertinence : on garde les autres candidats pour
            # que le lecteur voie que la 1re ligne est un choix, pas une verite
            "entites_portant_ce_nom": total,
            "autres_correspondances": [
                f"{e.get('siren')} - {e.get('nom_complet')}"
                for e in resultats if e.get("siren") != ent.get("siren")
            ][:10],
        }
    except (requests.RequestException, ValueError) as e:
        return {"erreur": f"{type(e).__name__}: {e}"}


def scraper_wikipedia(nom: str) -> dict:
    """Infobox et introduction de la page francophone."""
    url = f"https://fr.wikipedia.org/wiki/{nom.replace(' ', '_')}"
    if not robots_autorise(url):
        return {"erreur": "robots.txt de Wikipedia interdit cette page"}
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return {"erreur": f"HTTP {r.status_code}", "url": url}
        soup = BeautifulSoup(r.text, "lxml")

        infobox = {}
        table = soup.select_one("table.infobox, table.infobox_v3, table.wikitable")
        if table:
            for tr in table.select("tr"):
                th, td = tr.select_one("th"), tr.select_one("td")
                if th and td:
                    infobox[th.get_text(" ", strip=True)] = td.get_text(" ", strip=True)[:200]

        # un <p> a l'interieur de l'infobox precede l'introduction reelle :
        # sans le filtre find_parent("table"), on rapatrie la liste des filiales
        intro = next(
            (p.get_text(" ", strip=True)[:500]
             for p in soup.select("#mw-content-text p")
             if len(p.get_text(strip=True)) > 80 and not p.find_parent("table")),
            "",
        )
        return {"url": url, "nb_champs_infobox": len(infobox),
                "infobox": infobox, "intro": intro}
    except requests.RequestException as e:
        return {"erreur": f"{type(e).__name__}: {e}"}


def veille_presse(nom: str, nb_max: int = 10) -> list[dict]:
    """Articles recents mentionnant l'entite, via flux RSS de recherche."""
    url = FLUX_PRESSE.format(q=nom.replace(" ", "+"))
    if not robots_autorise(url):
        print(f"[!] robots.txt interdit {url.split('/')[2]} : veille presse ignoree")
        return []
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        flux = feedparser.parse(r.text)
    except requests.RequestException as e:
        print(f"[!] flux presse indisponible : {type(e).__name__}")
        return []

    return [
        {
            "titre": e.get("title", ""),
            "source": (e.get("source", {}) or {}).get("title", "") or url.split("/")[2],
            "date": e.get("published", ""),
            "lien": e.get("link", ""),
        }
        for e in flux.entries[:nb_max]
    ]


def construire_fiche(nom: str) -> dict:
    print(f"[*] Construction de la fiche : {nom}")
    fiche = {"entite": nom, "sources": ["SIRENE", "Wikipedia", "RSS presse"]}

    fiche["sirene"] = chercher_sirene(nom)
    time.sleep(DELAI)
    fiche["wikipedia"] = scraper_wikipedia(nom)
    time.sleep(DELAI)
    fiche["presse"] = veille_presse(nom)
    fiche["nb_articles"] = len(fiche["presse"])
    return fiche


def main():
    p = argparse.ArgumentParser(description="Fiche OSINT d'une entite publique")
    p.add_argument("nom", nargs="*", default=["TotalEnergies"])
    p.add_argument("--sortie", default="fiche_entite.json")
    args = p.parse_args()
    nom = " ".join(args.nom) if args.nom else "TotalEnergies"

    fiche = construire_fiche(nom)
    with open(args.sortie, "w", encoding="utf-8") as f:
        json.dump(fiche, f, indent=2, ensure_ascii=False)

    print(f"[+] Fiche : {args.sortie}")
    print(f"    SIREN            : {fiche['sirene'].get('siren', 'n/a')}")
    print(f"    Denomination     : {fiche['sirene'].get('denomination', 'n/a')}")
    print(f"    Champs infobox   : {fiche['wikipedia'].get('nb_champs_infobox', 0)}")
    print(f"    Articles presse  : {fiche['nb_articles']}")


if __name__ == "__main__":
    main()
