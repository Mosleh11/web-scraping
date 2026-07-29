import re

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

# La Depeche n'affiche pas de <time> : la date est dans le chemin de l'URL,
# sous la forme /2026/07/29/slug-13487060.php
RE_DATE_URL = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/")


class CleanPipeline:
    def process_item(self, item, spider):
        a = ItemAdapter(item)
        a["titre"] = re.sub(r"\s+", " ", a.get("titre") or "").strip()

        m = RE_DATE_URL.search(a.get("url") or "")
        a["date"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""

        if not a["titre"] or not a["date"]:
            raise DropItem(f"Article incomplet : {a.get('url')}")
        return item
