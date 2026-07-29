"""Defi 2 - impact de CONCURRENT_REQUESTS sur la vitesse du crawl AlloCine.

Deux series :
  A - reglages de politesse du TP (DOWNLOAD_DELAY=1 + AUTOTHROTTLE), 10 pages
  B - throttling desactive, 3 pages seulement pour limiter la charge

La serie B sert de temoin : sans elle on ne voit pas ce que fait reellement
CONCURRENT_REQUESTS, puisque le delai le neutralise.

Usage :
    python benchmark_scrapy.py
"""

import json
import re
import subprocess
import time

VALEURS = [1, 4, 8, 16]
DOSSIER = "allocine"

SERIES = {
    "A_politesse": {
        "pages": 10,
        "reglages": {"DOWNLOAD_DELAY": "1.0", "AUTOTHROTTLE_ENABLED": "True"},
    },
    "B_sans_throttling": {
        "pages": 3,
        "reglages": {"DOWNLOAD_DELAY": "0", "AUTOTHROTTLE_ENABLED": "False"},
    },
}

RE_STATS = {
    "items": re.compile(r"'item_scraped_count': (\d+)"),
    "responses": re.compile(r"'response_received_count': (\d+)"),
    "elapsed": re.compile(r"'elapsed_time_seconds': ([\d.]+)"),
}


def lancer(concurrence: int, pages: int, reglages: dict) -> dict:
    cmd = [
        "python", "-m", "scrapy", "crawl", "films",
        "-a", f"max_pages={pages}",
        "-s", f"CONCURRENT_REQUESTS={concurrence}",
        "-s", f"CONCURRENT_REQUESTS_PER_DOMAIN={concurrence}",
        # pas d'export : on mesure le crawl, pas l'ecriture disque
        "-s", "FEEDS={}",
        # -L INFO est indispensable : le dump des stats est emis au niveau INFO,
        # avec -L WARNING (suggere par l'enonce) il n'apparait pas du tout.
        "-L", "INFO",
    ]
    for cle, valeur in reglages.items():
        cmd += ["-s", f"{cle}={valeur}"]

    t0 = time.time()
    p = subprocess.run(cmd, cwd=DOSSIER, capture_output=True, text=True, errors="replace")
    mur = time.time() - t0

    sortie = p.stdout + p.stderr
    stats = {}
    for cle, motif in RE_STATS.items():
        m = motif.search(sortie)
        stats[cle] = float(m.group(1)) if m else None

    duree = stats["elapsed"] or mur
    items = int(stats["items"] or 0)
    responses = int(stats["responses"] or 0)
    return {
        "concurrence": concurrence,
        "temps": round(duree, 1),
        "items": items,
        "responses": responses,
        "items_par_s": round(items / duree, 2) if duree else 0,
        "ratio": round(items / responses, 3) if responses else 0,
    }


def tableau(nom: str, resultats: list[dict]) -> str:
    lignes = [
        f"### Serie {nom}",
        "",
        "| CONCURRENT_REQUESTS | temps (s) | items | items/s | items/responses |",
        "|---|---|---|---|---|",
    ]
    for r in resultats:
        lignes.append(
            f"| {r['concurrence']} | {r['temps']} | {r['items']} | "
            f"{r['items_par_s']} | {r['ratio']} |"
        )
    return "\n".join(lignes)


def main():
    tout = {}
    blocs = []
    for nom, conf in SERIES.items():
        print(f"\n=== Serie {nom} ({conf['pages']} pages, {conf['reglages']})")
        resultats = []
        for c in VALEURS:
            r = lancer(c, conf["pages"], conf["reglages"])
            resultats.append(r)
            print(f"  CONCURRENT_REQUESTS={c:2} -> {r['temps']:6.1f}s | {r['items']} items "
                  f"| {r['items_par_s']} items/s | ratio {r['ratio']}")
        tout[nom] = resultats
        blocs.append(tableau(nom, resultats))

    contenu = "# Benchmark CONCURRENT_REQUESTS (AlloCine)\n\n" + "\n\n".join(blocs) + "\n"
    print("\n" + contenu)
    with open("benchmark_scrapy.md", "w", encoding="utf-8") as f:
        f.write(contenu)
    with open("benchmark_scrapy.json", "w", encoding="utf-8") as f:
        json.dump(tout, f, indent=2)


if __name__ == "__main__":
    main()
