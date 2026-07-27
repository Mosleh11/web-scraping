"""Defi 2 - comparer deux exports CSV pour detecter les nouveautes.

Usage :
    python diff_scrapes.py articles_j1.csv articles_j2.csv
"""

import csv
import sys


def charger_urls(chemin: str) -> set:
    with open(chemin, encoding="utf-8") as f:
        return {row["url"] for row in csv.DictReader(f)}


def diff_scrapes(csv_ancien: str, csv_nouveau: str) -> dict:
    anciens = charger_urls(csv_ancien)
    nouveaux = charger_urls(csv_nouveau)
    return {
        "nouveaux": sorted(nouveaux - anciens),
        "disparus": sorted(anciens - nouveaux),
        "inchanges": len(anciens & nouveaux),
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage : python diff_scrapes.py <csv_ancien> <csv_nouveau>")
    r = diff_scrapes(sys.argv[1], sys.argv[2])
    print(f"Nouveaux : {len(r['nouveaux'])}")
    print(f"Disparus : {len(r['disparus'])}")
    print(f"Stables  : {r['inchanges']}")
    for u in r["nouveaux"][:10]:
        print(f"  + {u}")
