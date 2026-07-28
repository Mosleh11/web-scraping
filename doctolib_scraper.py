"""TD 2.1 - Doctolib : fiches praticiens d'une specialite dans une ville.

Usage :
    python doctolib_scraper.py
    python doctolib_scraper.py --specialite dentiste --ville paris --visible
"""

import argparse
import json
import re

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from selenium_utils import (
    accepter_cookies,
    make_driver,
    screenshot,
    scroll_jusqu_a_stabilite,
)

# Defi 3 : cascade de selecteurs de carte, du plus precis au plus generique.
# 'div.dl-card' est le selecteur observe aujourd'hui ; les suivants sont des
# filets de securite, dont celui de l'enonce qui ne renvoie plus rien.
CARTES_CANDIDATES = [
    "div.dl-card",
    "div[data-test='search-result-card']",
    "article",
]


COMPTEUR_JS = (
    "return [...document.querySelectorAll(arguments[0])]"
    ".filter(c => c.querySelector('h2')).length"
)


def selecteur_carte(driver, timeout: int = 25) -> str:
    """Premier selecteur candidat qui trouve des cartes porteuses d'un h2.

    Les <div.dl-card> apparaissent dans le DOM avant que React n'y injecte le
    nom du praticien : on attend donc la condition utile (une carte AVEC un h2)
    et non la simple presence du conteneur.
    """
    def premier_qui_marche(d):
        for css in CARTES_CANDIDATES:
            if d.execute_script(COMPTEUR_JS, css):
                return css
        return False

    try:
        css = WebDriverWait(driver, timeout).until(premier_qui_marche)
    except TimeoutException as e:
        screenshot(driver, "doctolib_erreur")
        raise RuntimeError(
            f"Aucun selecteur de carte ne fonctionne : {CARTES_CANDIDATES}"
        ) from e
    if css != CARTES_CANDIDATES[0]:
        print(f"Selecteur principal KO, repli sur '{css}'")
    return css


# L'extraction se fait en JS : les cartes hors viewport sont dans le DOM mais
# .text de Selenium renvoie du vide pour un element non rendu a l'ecran.
EXTRACTION_JS = r"""
const cards = [...document.querySelectorAll(arguments[0])]
    .filter(c => c.querySelector('h2'));
return cards.map(c => ({
    lignes: (c.innerText || '').split('\n').map(s => s.trim()).filter(Boolean),
    texte: c.innerText || '',
    url: (c.querySelector("a[href*='/']") || {}).href || '',
}));
"""

RE_HEURE = re.compile(r"^\d{1,2}[:h]\d{2}$")
RE_PROCHAIN = re.compile(r"Prochain RDV le ([^\n]+)")
RE_CP = re.compile(r"^\d{5}\s")


def trouver_nom(lignes: list[str]) -> str:
    """Fallback en cascade : la premiere ligne non vide fait office de nom."""
    return lignes[0] if lignes else "n/a"


def trouver_adresse(lignes: list[str]) -> str:
    """L'adresse = la ligne qui precede le code postal, plus la ligne CP+ville."""
    for i, ligne in enumerate(lignes):
        if RE_CP.match(ligne):
            rue = lignes[i - 1] if i >= 1 else ""
            return f"{rue}, {ligne}".strip(", ")
    return "n/a"


def parser_carte(brut: dict) -> dict:
    lignes = brut["lignes"]
    texte = brut["texte"]
    nom = trouver_nom(lignes)
    specialite = lignes[1] if len(lignes) > 1 else "n/a"

    types = ["Cabinet"]
    if re.search(r"visio|vid[ée]o", texte, re.I):
        types.append("Video")

    creneaux = [l for l in lignes if RE_HEURE.match(l)][:3]
    prochain = RE_PROCHAIN.search(texte)

    return {
        "nom_specialite": f"{nom} - {specialite}",
        "adresse": trouver_adresse(lignes),
        "type_consultation": types,
        "prochains_creneaux": creneaux,
        "prochain_rdv": prochain.group(1).strip() if prochain else "",
        "url_fiche": brut["url"].split("?")[0],
    }


def scraper(specialite: str, ville: str, limite: int, headless: bool) -> list[dict]:
    url = f"https://www.doctolib.fr/{specialite}/{ville}"
    driver = make_driver(headless=headless)
    try:
        print(f"Ouverture de {url}")
        driver.get(url)
        accepter_cookies(driver)

        css = selecteur_carte(driver)
        print(f"Resultats charges : {len(driver.find_elements(By.CSS_SELECTOR, css))} cartes ({css})")

        total = scroll_jusqu_a_stabilite(driver, COMPTEUR_JS, css)
        print(f"Apres scroll : {total} fiches praticiens")

        brut = driver.execute_script(EXTRACTION_JS, css)
        fiches = [parser_carte(b) for b in brut][:limite]

        if not fiches:
            screenshot(driver, "doctolib_aucune_fiche")
        return fiches
    finally:
        driver.quit()


def main():
    p = argparse.ArgumentParser(description="Scraper Doctolib")
    p.add_argument("--specialite", default="osteopathe")
    p.add_argument("--ville", default="paris")
    p.add_argument("--limite", type=int, default=10)
    p.add_argument("--sortie", default="doctolib.json")
    p.add_argument("--visible", action="store_true", help="desactive le mode headless")
    args = p.parse_args()

    fiches = scraper(args.specialite, args.ville, args.limite, headless=not args.visible)
    with open(args.sortie, "w", encoding="utf-8") as f:
        json.dump(fiches, f, indent=2, ensure_ascii=False)

    avec_creneaux = sum(1 for f in fiches if f["prochains_creneaux"])
    print(f"{len(fiches)} praticiens exportes dans {args.sortie}")
    print(f"dont {avec_creneaux} avec des creneaux horaires affiches")


if __name__ == "__main__":
    main()
