"""Defi 1 (suite) - valider la strategie 2 : bypasser la banniere par injection.

Reprend les valeurs relevees par defi_cookies.py et teste quelles combinaisons
de cookies suffisent a ne plus voir la banniere Didomi.

Usage :
    python defi_cookies.py && python defi_injection.py
"""

import json

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from selenium_utils import make_driver

ACCUEIL = "https://www.doctolib.fr/"
CIBLE = "https://www.doctolib.fr/osteopathe/paris"
BOUTON = "didomi-notice-agree-button"


def banniere_visible(driver, timeout: int = 8) -> bool:
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.find_elements(By.ID, BOUTON)
        )
        return True
    except Exception:
        return False


def essai(label: str, noms: list[str], valeurs: dict) -> bool:
    driver = make_driver(headless=True)
    try:
        # il faut etre sur le domaine avant de pouvoir y poser un cookie
        driver.get(ACCUEIL)
        for nom in noms:
            driver.add_cookie({"name": nom, "value": valeurs[nom], "domain": ".doctolib.fr"})
        driver.get(CIBLE)
        visible = banniere_visible(driver)
        print(f"{label:32} banniere visible : {visible}")
        return visible
    finally:
        driver.quit()


if __name__ == "__main__":
    with open("defi_cookies.json", encoding="utf-8") as f:
        valeurs = json.load(f)[0]["cookies_consentement"]

    resultats = {
        "aucun cookie": essai("aucun cookie", [], valeurs),
        "euconsent-v2 seul": essai("euconsent-v2 seul", ["euconsent-v2"], valeurs),
        "euconsent-v2 + didomi_token": essai(
            "euconsent-v2 + didomi_token", ["euconsent-v2", "didomi_token"], valeurs
        ),
    }
    with open("defi_injection.json", "w", encoding="utf-8") as f:
        json.dump(resultats, f, indent=2, ensure_ascii=False)
    print("\nRapport ecrit dans defi_injection.json")
