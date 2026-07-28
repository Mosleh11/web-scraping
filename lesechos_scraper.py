"""TD 2.2 - Les Echos : articles a la une.

Usage :
    python lesechos_scraper.py
    python lesechos_scraper.py --limite 20 --visible
    python lesechos_scraper.py --benchmark    # compare headless vs fenetre visible
"""

import argparse
import json

import requests
from bs4 import BeautifulSoup

from selenium_utils import UA_CHROME, attendre_presence, chrono, make_driver, screenshot

URL = "https://www.lesechos.fr"
ARTICLE_CSS = "article"

COMPTEUR_JS = "return document.querySelectorAll('article').length"

# Les classes sont des hash styled-components (sc-19z4l96-2...) : illisibles et
# regenerees a chaque build. On ne s'appuie que sur des ancres stables :
# la balise <article>, le <h3> du titre, le href, et data-testid=subscribe-badge.
EXTRACTION_JS = r"""
const vus = new Set();
const out = [];
for (const art of document.querySelectorAll('article')) {
    const a = art.querySelector('a[href]');
    const h = art.querySelector('h3, h2');
    if (!a || !h) continue;
    const url = a.href.split('?')[0];
    const badges = [...art.querySelectorAll('[data-testid="subscribe-badge"]')]
        .map(b => (b.innerText || '').trim()).filter(Boolean);
    // le badge PREMIUM est rendu a l'interieur du <h3> : on le retire du titre
    let titre = (h.innerText || '');
    for (const b of badges) titre = titre.split(b).join(' ');
    titre = titre.replace(/\s+/g, ' ').trim();
    if (!titre || vus.has(url)) continue;
    vus.add(url);
    out.push({titre: titre, url: url, badges: badges});
}
return out;
"""


def diagnostic_requests() -> dict:
    """Etape 1 de l'enonce : verifier si requests suffirait."""
    resultat = {}
    for label, ua in [
        ("UA scraper honnete", "IPSSI-scraper (+contact@ipssi.fr)"),
        ("UA Chrome", UA_CHROME),
    ]:
        try:
            r = requests.get(URL, headers={"User-Agent": ua}, timeout=15)
            soup = BeautifulSoup(r.text, "lxml")
            resultat[label] = {
                "status": r.status_code,
                "octets": len(r.text),
                "titres": len(soup.select("h2, h3")),
            }
        except requests.RequestException as e:
            resultat[label] = {"erreur": str(e)}
        print(f"requests / {label:20} -> {resultat[label]}")
    return resultat


def rubrique_depuis_url(url: str) -> str:
    morceaux = [m for m in url.replace("https://", "").split("/") if m]
    return morceaux[1].replace("-", " ").capitalize() if len(morceaux) > 2 else ""


def collecter_une(driver, limite: int) -> list[dict]:
    driver.get(URL)
    attendre_presence(driver, ARTICLE_CSS, timeout=25, nom_erreur="lesechos_erreur")
    brut = driver.execute_script(EXTRACTION_JS)
    print(f"{len(brut)} articles uniques trouves a la une")
    return [
        {
            "titre": a["titre"],
            "rubrique": rubrique_depuis_url(a["url"]),
            "chapeau": "",
            "heure_publi": "",
            "premium": "PREMIUM" in a["badges"],
            "url": a["url"],
        }
        for a in brut
    ][:limite]


def enrichir(driver, articles: list[dict]) -> None:
    """Chapo, heure et rubrique exacte viennent des meta de la fiche article.

    La une n'affiche ni chapo ni heure pour la majorite des cartes : seules les
    balises meta (accessibles sans franchir le paywall) portent l'information.
    """
    for i, art in enumerate(articles, 1):
        try:
            driver.get(art["url"])
            attendre_presence(driver, "head meta", timeout=15, nom_erreur="lesechos_meta")
            metas = driver.execute_script(
                """
                const g = s => (document.querySelector(s) || {}).content || '';
                return {
                    desc: g('meta[name="description"]') || g('meta[property="og:description"]'),
                    date: g('meta[property="article:published_time"]'),
                    section: g('meta[property="article:section"]'),
                };
                """
            )
            art["chapeau"] = metas["desc"][:300]
            art["heure_publi"] = metas["date"]
            if metas["section"]:
                art["rubrique"] = metas["section"]
        except (RuntimeError, Exception) as e:
            print(f"Meta indisponibles pour {art['url']} : {e.__class__.__name__}")
        if i % 5 == 0:
            print(f"Enrichissement : {i}/{len(articles)}")


def benchmark(limite: int, repetitions: int = 3) -> dict:
    """Compare headless vs fenetre visible, demarrage du driver inclus et exclu."""
    mesures = {}
    for label, headless in [("visible", False), ("headless", True)]:
        totaux, pages = [], []
        for _ in range(repetitions):
            (driver, t_boot) = chrono(make_driver, headless)
            try:
                _, t_page = chrono(collecter_une, driver, limite)
            finally:
                driver.quit()
            totaux.append(t_boot + t_page)
            pages.append(t_page)
        mesures[label] = {
            "total_moyen": round(sum(totaux) / repetitions, 2),
            "page_moyen": round(sum(pages) / repetitions, 2),
        }
        print(f"{label:9} : total {mesures[label]['total_moyen']}s "
              f"| page seule {mesures[label]['page_moyen']}s")

    for cle in ("total_moyen", "page_moyen"):
        gain = mesures["visible"][cle] / mesures["headless"][cle]
        mesures[f"gain_{cle}"] = round(gain, 2)
        print(f"Gain headless ({cle}) : x{gain:.2f}")
    return mesures


def main():
    p = argparse.ArgumentParser(description="Scraper Les Echos")
    p.add_argument("--limite", type=int, default=15)
    p.add_argument("--sortie", default="lesechos.json")
    p.add_argument("--visible", action="store_true")
    p.add_argument("--benchmark", action="store_true")
    p.add_argument("--no-enrichir", action="store_true")
    args = p.parse_args()

    print("--- Diagnostic : requests suffit-il ?")
    diagnostic_requests()

    if args.benchmark:
        print("\n--- Benchmark headless vs visible")
        mesures = benchmark(args.limite)
        with open("benchmark_headless.json", "w", encoding="utf-8") as f:
            json.dump(mesures, f, indent=2)
        return

    print("\n--- Collecte Selenium")
    driver = make_driver(headless=not args.visible)
    try:
        articles = collecter_une(driver, args.limite)
        if not articles:
            screenshot(driver, "lesechos_aucun_article")
        if not args.no_enrichir:
            enrichir(driver, articles)
    finally:
        driver.quit()

    with open(args.sortie, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    premium = sum(1 for a in articles if a["premium"])
    print(f"{len(articles)} articles exportes dans {args.sortie} ({premium} premium)")


if __name__ == "__main__":
    main()
