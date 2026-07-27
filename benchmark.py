"""Defi 3 - mesurer le cout reel du throttling.

Mesure la duree de collecte de 2, 5 et 10 pages d'archive pour DELAY = 0.5 / 1 / 2 s.
Ecrit le tableau de resultats dans benchmark_resultats.md.

Usage :
    python benchmark.py
"""

import time

import scraper_bdm
from scraper_bdm import DOMAINE, get_page, parse_articles

PAGES = [2, 5, 10]
DELAIS = [0.5, 1.0, 2.0]
RUBRIQUE = "web"


def mesurer(nb_pages: int, delai: float) -> tuple[float, int]:
    scraper_bdm.DELAI = delai
    t0 = time.time()
    total = 0
    for page in range(1, nb_pages + 1):
        url = f"{DOMAINE}/{RUBRIQUE}/" if page == 1 else f"{DOMAINE}/{RUBRIQUE}/page/{page}/"
        total += len(parse_articles(get_page(url)))
        if page < nb_pages:
            time.sleep(delai)
    return time.time() - t0, total


def main():
    resultats = {}
    for nb in PAGES:
        for d in DELAIS:
            duree, articles = mesurer(nb, d)
            resultats[(nb, d)] = duree
            print(f"{nb} pages @ {d}s -> {duree:.1f}s ({articles} articles)")
            time.sleep(2)

    lignes = ["| Pages | 0.5 s | 1.0 s | 2.0 s |", "|-------|-------|-------|-------|"]
    for nb in PAGES:
        cells = " | ".join(f"{resultats[(nb, d)]:.1f} s" for d in DELAIS)
        lignes.append(f"| {nb} | {cells} |")

    tableau = "\n".join(lignes)
    print("\n" + tableau)
    with open("benchmark_resultats.md", "w", encoding="utf-8") as f:
        f.write("# Benchmark du throttling\n\n" + tableau + "\n")


if __name__ == "__main__":
    main()
