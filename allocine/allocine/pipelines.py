import re

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

RE_ANNEE = re.compile(r"(?:19|20)\d{2}")


class CleanPipeline:
    """Trim les textes, extrait l'annee, caste les notes en float."""

    def process_item(self, item, spider):
        a = ItemAdapter(item)

        for champ in ("titre", "realisateur"):
            a[champ] = (a.get(champ) or "").strip()

        # la date de sortie arrive sous la forme "4 septembre 2024"
        annee = RE_ANNEE.search(a.get("annee") or "")
        a["annee"] = int(annee.group(0)) if annee else None

        for champ in ("note_presse", "note_spectateurs"):
            brut = (a.get(champ) or "").replace(",", ".").strip()
            try:
                a[champ] = float(brut)
            except (ValueError, TypeError):
                a[champ] = None

        return item


class ValidationPipeline:
    """Un film sans titre n'a aucune valeur : on le sort du flux."""

    def process_item(self, item, spider):
        a = ItemAdapter(item)
        if not a.get("titre"):
            raise DropItem(f"Titre manquant : {a.get('url')}")
        return item
