"""Defi 3 - Wikipedia suit-il l'actualite captee par la veille ?

Croise les mentions de veille.db avec l'historique des revisions de la page
Wikipedia de la cible, pour mesurer le decalage entre un evenement rapporte
par la presse et son enregistrement dans l'encyclopedie.

Note d'acces : fr.wikipedia.org interdit /w/ dans son robots.txt, donc
api.php et rest.php sont hors limites. On passe par api.wikimedia.org, l'API
publique officielle, dont le robots.txt autorise cet appel.

Usage :
    cd veille && python ../defi3_wikipedia.py TotalEnergies
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

HEADERS = {"User-Agent": "IPSSI-OSINT (+cours@ipssi.fr)"}
API_HISTORIQUE = "https://api.wikimedia.org/core/v1/wikipedia/fr/page/{titre}/history"


def historique(titre: str) -> list[dict]:
    r = requests.get(API_HISTORIQUE.format(titre=titre.replace(" ", "_")),
                     headers=HEADERS, timeout=25)
    r.raise_for_status()
    return [
        {
            "date": rev["timestamp"][:10],
            "horodatage": rev["timestamp"],
            "commentaire": (rev.get("comment") or "").strip(),
            "auteur_anonyme": (rev.get("user") or {}).get("id") is None,
        }
        for rev in r.json().get("revisions", [])
    ]


def date_article(brut: str) -> str:
    """Les dates RSS arrivent au format RFC 822 ou ISO selon la source."""
    if not brut:
        return ""
    try:
        return parsedate_to_datetime(brut).date().isoformat()
    except (TypeError, ValueError):
        return brut[:10]


def main():
    cible = " ".join(sys.argv[1:]) or "TotalEnergies"

    cx = sqlite3.connect("veille.db")
    mentions = [
        {"score": s, "titre": t, "date": date_article(d), "url": u}
        for s, t, d, u in cx.execute(
            "SELECT score_alerte, titre, date_publi, url FROM mentions "
            "WHERE score_alerte > 0 ORDER BY score_alerte DESC")
    ]
    cx.close()

    revisions = historique(cible)
    print(f"{len(mentions)} mentions alertantes | {len(revisions)} revisions Wikipedia")
    if not revisions:
        return

    derniere = revisions[0]
    aujourdhui = datetime.now(timezone.utc).date()
    age = (aujourdhui - datetime.fromisoformat(derniere["date"]).date()).days
    print(f"\nDerniere revision : {derniere['date']} ({age} jours) "
          f"-- {derniere['commentaire'][:70]}")
    print(f"Periode couverte  : {revisions[-1]['date']} -> {revisions[0]['date']}")

    print("\n=== Un evenement de presse a-t-il une revision posterieure ?")
    dates_revisions = [datetime.fromisoformat(r["date"]).date() for r in revisions]
    rapport = []
    for m in mentions:
        if not m["date"]:
            continue
        jour = datetime.fromisoformat(m["date"]).date()
        posterieures = [d for d in dates_revisions if d >= jour]
        delai = (min(posterieures) - jour).days if posterieures else None
        rapport.append({**m, "delai_jours": delai})
        etat = f"revision a J+{delai}" if delai is not None else "AUCUNE revision depuis"
        print(f"  [{m['score']}] {m['date']} {m['titre'][:52]:52} -> {etat}")

    jamais = [r for r in rapport if r["delai_jours"] is None]
    print(f"\n{len(jamais)}/{len(rapport)} evenements ne sont suivis d'aucune revision")

    with open("defi3_wikipedia.json", "w", encoding="utf-8") as f:
        json.dump({"cible": cible, "derniere_revision": derniere,
                   "age_derniere_revision_jours": age,
                   "mentions": rapport}, f, indent=2, ensure_ascii=False)
    print("Rapport : defi3_wikipedia.json")


if __name__ == "__main__":
    main()
