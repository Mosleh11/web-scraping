"""Defi 1 - inventaire des cookies deposes apres acceptation.

Equivalent programmatique de DevTools > Application > Cookies : on lit le
cookie jar du navigateur avant et apres le clic sur "Tout accepter".

Usage :
    python defi_cookies.py
"""

import json

from selenium_utils import accepter_cookies, make_driver

CIBLES = [
    ("doctolib", "https://www.doctolib.fr/osteopathe/paris"),
    ("maiia", "https://www.maiia.com"),
]


def inventaire(driver) -> list[dict]:
    """driver.get_cookies() ne renvoie que le domaine courant.

    On passe par CDP (Network.getAllCookies) pour voir aussi les cookies
    deposes par les domaines tiers, comme le ferait DevTools > Application.
    """
    maintenant = driver.execute_script("return Math.floor(Date.now()/1000)")
    bruts = driver.execute_cdp_cmd("Network.getAllCookies", {})["cookies"]
    return sorted(
        (
            {
                "nom": c["name"],
                "domaine": c.get("domain", ""),
                "duree_jours": round((c["expires"] - maintenant) / 86400, 1)
                if c.get("expires", -1) > 0 else "session",
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", False),
                "taille_valeur": len(c.get("value", "")),
                "valeur_encodee": not c.get("value", "").isalnum(),
            }
            for c in bruts
        ),
        key=lambda c: c["nom"],
    )


def analyser(nom: str, url: str) -> dict:
    driver = make_driver(headless=True)
    try:
        driver.get(url)
        avant = inventaire(driver)
        selecteur = accepter_cookies(driver)
        driver.refresh()
        apres = inventaire(driver)

        noms_avant = {c["nom"] for c in avant}
        ajoutes = [c for c in apres if c["nom"] not in noms_avant]
        domaine_principal = "." + ".".join(url.split("/")[2].split(".")[-2:])
        tiers = [c for c in apres if not c["domaine"].endswith(domaine_principal.lstrip("."))]

        print(f"\n=== {nom} ({url})")
        print(f"bouton d'acceptation : {selecteur}")
        print(f"cookies avant : {len(avant)} | apres : {len(apres)} | ajoutes : {len(ajoutes)}")
        print(f"cookies de domaine tiers : {len(tiers)}")
        for c in apres[:20]:
            print(f"  {c['nom'][:34]:34} {c['domaine'][:24]:24} "
                  f"{str(c['duree_jours']):>8} j  {c['taille_valeur']:>5} o")

        consentement = {
            c["name"]: c["value"]
            for c in driver.execute_cdp_cmd("Network.getAllCookies", {})["cookies"]
            if c["name"] in ("didomi_token", "euconsent-v2", "tarteaucitron", "OptanonConsent")
        }
        print("cookies de consentement (a injecter en strategie 2) :")
        for k, v in consentement.items():
            print(f"  {k} = {v[:70]}{'...' if len(v) > 70 else ''}")

        return {
            "site": nom,
            "cookies_consentement": consentement,
            "url": url,
            "bouton": selecteur,
            "avant": avant,
            "apres": apres,
            "ajoutes": [c["nom"] for c in ajoutes],
            "tiers": [c["nom"] for c in tiers],
        }
    finally:
        driver.quit()


if __name__ == "__main__":
    rapport = [analyser(nom, url) for nom, url in CIBLES]
    with open("defi_cookies.json", "w", encoding="utf-8") as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)
    print("\nRapport ecrit dans defi_cookies.json")
