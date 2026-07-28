"""Briques communes aux deux scrapers Selenium du jour 2."""

import os
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

SCREENSHOTS = "screenshots"

# Chrome headless annonce "HeadlessChrome/xxx" dans son User-Agent, ce que
# certains WAF suffisent a bloquer. On force donc l'UA d'un Chrome normal.
UA_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
)

# Selecteurs de bouton d'acceptation, du plus specifique au plus generique.
BOUTONS_COOKIES = [
    (By.ID, "didomi-notice-agree-button"),
    (By.CSS_SELECTOR, "button#onetrust-accept-btn-handler"),
    (By.XPATH, "//button[contains(., 'Tout accepter') or contains(., 'Accepter')]"),
]


def make_driver(headless: bool = True, images: bool = False) -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(f"--user-agent={UA_CHROME}")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    if not images:
        opts.add_experimental_option(
            "prefs",
            {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2,
            },
        )
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(60)
    return driver


def screenshot(driver, nom: str) -> str:
    os.makedirs(SCREENSHOTS, exist_ok=True)
    chemin = os.path.join(SCREENSHOTS, f"{nom}.png")
    try:
        driver.save_screenshot(chemin)
        print(f"Screenshot : {chemin}")
    except WebDriverException as e:
        print(f"Screenshot impossible : {e}")
    return chemin


def accepter_cookies(driver, timeout: int = 8) -> str:
    """Strategie 1 : cliquer. Renvoie le selecteur qui a marche, ou 'aucune'."""
    for by, valeur in BOUTONS_COOKIES:
        try:
            btn = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, valeur))
            )
            btn.click()
            print(f"Banniere cookies acceptee via {by}={valeur}")
            return f"{by}={valeur}"
        except TimeoutException:
            continue
    print("Aucune banniere cookies detectee")
    return "aucune"


def attendre_presence(driver, css: str, timeout: int = 20, nom_erreur: str = "erreur"):
    """WebDriverWait + screenshot automatique si la condition n'arrive pas."""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css))
        )
    except TimeoutException as e:
        screenshot(driver, nom_erreur)
        raise RuntimeError(f"Element '{css}' absent apres {timeout}s") from e


def scroll_jusqu_a_stabilite(driver, compteur_js: str, *args, tours: int = 6) -> int:
    """Scrolle tant que le nombre d'elements cibles augmente.

    On attend une *condition* (le compteur a bouge) plutot qu'une duree fixe :
    un poll court par WebDriverWait au lieu d'un time.sleep(1.5) arbitraire.
    """
    total = driver.execute_script(compteur_js, *args)
    for _ in range(tours):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        avant = total
        try:
            WebDriverWait(driver, 4).until(
                lambda d: d.execute_script(compteur_js, *args) > avant
            )
        except TimeoutException:
            break
        total = driver.execute_script(compteur_js, *args)
    return total


def chrono(fn, *args, **kwargs):
    t0 = time.time()
    resultat = fn(*args, **kwargs)
    return resultat, time.time() - t0
