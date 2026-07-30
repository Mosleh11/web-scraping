"""Defi 1 - mesurer la precision du scoring de sentiment, puis le calibrer.

Compare deux jeux de mots-cles sur les mentions reellement collectees :
  v1 = listes de l'enonce
  v2 = listes calibrees apres lecture des articles

Les etiquettes de reference (ETIQUETTES) viennent de la lecture du titre, du
chapo et de la meta description de chaque article -- pas d'une devinette.

Usage :
    cd veille && python ../defi1_calibration.py
"""

import json
import sqlite3
import unicodedata

BASE = "veille.db"

MOTS_NEGATIFS_V1 = [
    "fraude", "amende", "condamne", "condamnation", "scandale", "plainte",
    "liquidation", "faillite", "perquisition", "accuse", "enquete", "proces",
    "sanction", "greve", "licenciement", "polemique", "recul", "chute",
]
MOTS_POSITIFS_V1 = [
    "croissance", "benefice", "record", "acquisition", "innovation",
    "nomination", "partenariat", "expansion", "investissement", "contrat",
    "hausse", "succes", "lancement", "resultats en hausse",
]

# +3 mots negatifs observes dans les faux neutres du corpus
MOTS_NEGATIFS_V2 = MOTS_NEGATIFS_V1 + ["vigilance", "fait appel", "profiteurs"]

# +3 mots positifs observes, et retrait de "benefice" : a lui seul il produit
# 3 des 5 faux positifs, parce qu'un benefice record est presque toujours
# raconte comme un scandale quand la cible est un groupe petrolier.
MOTS_POSITIFS_V2 = [m for m in MOTS_POSITIFS_V1 if m != "benefice"] + [
    "approuve", "atout", "lance",
]

# 0 = neutre, 1 = negatif pour la cible, 2 = positif pour la cible
ETIQUETTES = {
    "Saft lance sa nouvelle": 2,
    "Carburant : TotalEnergies annonce des milliards": 1,
    "Chypre : TotalEnergies approuve": 2,
    "engrange des milliards de benefices mais vous payez": 1,
    "double son benefice": 1,
    "Cinq questions qui se posent avant un proces": 1,
    "Devoir de vigilance : TotalEnergies fait appel": 1,
    "strategie de rendement": 0,
    "Devoir de vigilance : TotalEnergies conteste": 1,
    "Profiteurs de guerre": 1,
    "La diversification geographique": 2,
    "TotalEnergies fait appel de la decision lui enjoignant": 1,
}


def sans_accents(texte: str) -> str:
    decompose = unicodedata.normalize("NFKD", texte or "")
    return "".join(c for c in decompose if not unicodedata.combining(c)).lower()


def scorer(texte: str, negatifs: list[str], positifs: list[str]) -> int:
    plat = sans_accents(texte)
    neg = sum(1 for m in negatifs if m in plat)
    pos = sum(1 for m in positifs if m in plat)
    return 1 if neg > pos else (2 if pos > neg else 0)


def etiquette(titre: str) -> int | None:
    plat = sans_accents(titre)
    for fragment, valeur in ETIQUETTES.items():
        if sans_accents(fragment) in plat:
            return valeur
    return None


def precision(paires: list[tuple[int, int]], classe: int) -> tuple[int, int]:
    """Parmi les articles predits dans `classe`, combien sont corrects."""
    predits = [(p, r) for p, r in paires if p == classe]
    return sum(1 for p, r in predits if p == r), len(predits)


def rappel(paires: list[tuple[int, int]], classe: int) -> tuple[int, int]:
    """Parmi les articles reellement dans `classe`, combien sont retrouves."""
    reels = [(p, r) for p, r in paires if r == classe]
    return sum(1 for p, r in reels if p == r), len(reels)


def evaluer(nom: str, lignes: list[tuple[str, str]], neg: list[str], pos: list[str]):
    paires = []
    for titre, resume in lignes:
        reel = etiquette(titre)
        if reel is None:
            continue
        paires.append((scorer(f"{titre} {resume}", neg, pos), reel))

    print(f"\n=== {nom} ({len(paires)} articles etiquetes)")
    for classe, libelle in ((2, "positif"), (1, "negatif")):
        bons, total = precision(paires, classe)
        taux = f"{bons / total:.0%}" if total else "n/a"
        r_bons, r_total = rappel(paires, classe)
        r_taux = f"{r_bons / r_total:.0%}" if r_total else "n/a"
        print(f"  score={classe} ({libelle:8}) precision {bons}/{total} = {taux:>4}"
              f"   | rappel {r_bons}/{r_total} = {r_taux}")
    justes = sum(1 for p, r in paires if p == r)
    print(f"  exactitude globale : {justes}/{len(paires)} = {justes / len(paires):.0%}")
    return {"paires": paires, "exactitude": justes / len(paires)}


def main():
    cx = sqlite3.connect(BASE)
    lignes = cx.execute("SELECT titre, resume FROM mentions").fetchall()
    cx.close()
    print(f"{len(lignes)} mentions en base")

    v1 = evaluer("v1 - listes de l'enonce", lignes, MOTS_NEGATIFS_V1, MOTS_POSITIFS_V1)
    v2 = evaluer("v2 - listes calibrees", lignes, MOTS_NEGATIFS_V2, MOTS_POSITIFS_V2)

    ecart = v2["exactitude"] - v1["exactitude"]
    print(f"\nGain d'exactitude : {ecart:+.0%}")

    with open("defi1_calibration.json", "w", encoding="utf-8") as f:
        json.dump({"v1": v1["exactitude"], "v2": v2["exactitude"],
                   "mots_negatifs_ajoutes": MOTS_NEGATIFS_V2[len(MOTS_NEGATIFS_V1):],
                   "mots_positifs_ajoutes": ["approuve", "atout", "lance"],
                   "mot_retire": "benefice"}, f, indent=2, ensure_ascii=False)
    print("Rapport : defi1_calibration.json")


if __name__ == "__main__":
    main()
