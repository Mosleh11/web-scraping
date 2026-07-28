"""Defi 2 - mesurer la detectabilite du driver sur bot.sannysoft.com.

Trois configurations comparees : brute, avec flags anti-detection, et headless.
Screenshots dans screenshots/, resultats lisibles dans defi_antibot.json.

Usage :
    python defi_antibot.py
"""

import json
import time

from selenium import webdriver

from selenium_utils import UA_CHROME, screenshot

URL = "https://bot.sannysoft.com"

# On ne garde que les lignes portant un verdict (classe passed/failed) : les
# deux premiers tableaux de sannysoft. Le troisieme n'est qu'un dump brut.
LECTURE_JS = r"""
const out = {};
for (const tr of document.querySelectorAll('table tr')) {
    const td = tr.querySelectorAll('td');
    if (td.length < 2) continue;
    const classe = td[1].className || '';
    if (!classe.includes('passed') && !classe.includes('failed')) continue;
    out[td[0].innerText.trim()] = {
        valeur: td[1].innerText.trim().replace(/\s+/g, ' ').slice(0, 80),
        verdict: classe.includes('failed') ? 'ROUGE' : 'VERT',
    };
}
return out;
"""


def config(nom: str, headless: bool, stealth: bool, ua: bool = True) -> dict:
    opts = webdriver.ChromeOptions()
    if headless:
        opts.add_argument("--headless=new")
        if ua:
            opts.add_argument("--user-agent=" + UA_CHROME)
    opts.add_argument("--window-size=1920,1080")
    if stealth:
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=opts)
    try:
        driver.get(URL)
        time.sleep(3)  # page de test statique : pas d'element a attendre
        resultats = driver.execute_script(LECTURE_JS)
        screenshot(driver, f"antibot_{nom}")
        return resultats
    finally:
        driver.quit()


def main():
    configs = [
        ("brut", False, False, True),
        ("stealth", False, True, True),
        ("headless_sans_ua", True, True, False),
        ("headless_avec_ua", True, True, True),
    ]
    rapport = {}
    for nom, headless, stealth, ua in configs:
        print(f"\n=== {nom} (headless={headless}, stealth={stealth}, ua_force={ua})")
        rapport[nom] = config(nom, headless, stealth, ua)
        for cle, v in rapport[nom].items():
            print(f"  {cle:26} {v['verdict']:6} {v['valeur'][:60]}")

    print("\n=== Lignes dont le verdict change selon la configuration")
    cles = set().union(*(r.keys() for r in rapport.values()))
    for cle in sorted(cles):
        verdicts = {n: rapport[n].get(cle, {}).get("verdict", "?") for n in rapport}
        if len(set(verdicts.values())) > 1:
            print(f"  {cle:26} {verdicts}")

    with open("defi_antibot.json", "w", encoding="utf-8") as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)
    print("\nRapport ecrit dans defi_antibot.json")


if __name__ == "__main__":
    main()
