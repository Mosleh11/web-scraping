import sqlite3

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

DDL = """CREATE TABLE IF NOT EXISTS actions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    libelle    TEXT NOT NULL,
    cours      REAL,
    variation  REAL,
    volume     INTEGER,
    isin       TEXT UNIQUE,
    scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
)"""


def _nombre(brut: str) -> str:
    """Boursorama ecrit '2 820,9305' : espace fine comme separateur de milliers."""
    return (
        (brut or "")
        .replace("\u202f", "")
        .replace("\xa0", "")
        .replace(" ", "")
        .replace("%", "")
        .replace(",", ".")
        .strip()
    )


class CleanPipeline:
    """Caste les colonnes numeriques, trim le libelle."""

    def process_item(self, item, spider):
        a = ItemAdapter(item)
        a["libelle"] = (a.get("libelle") or "").strip()
        a["isin"] = (a.get("isin") or "").strip()

        for champ in ("cours", "variation"):
            try:
                a[champ] = float(_nombre(a.get(champ)))
            except (ValueError, TypeError):
                a[champ] = None
        try:
            a["volume"] = int(float(_nombre(a.get("volume"))))
        except (ValueError, TypeError):
            a["volume"] = None
        return item


class ValidationPipeline:
    def process_item(self, item, spider):
        a = ItemAdapter(item)
        if not a.get("libelle") or not a.get("isin"):
            raise DropItem(f"Ligne incomplete : {dict(a)}")
        return item


class SQLitePipeline:
    def open_spider(self, spider):
        self.cx = sqlite3.connect("bourse.db")
        self.cx.execute(DDL)
        self.cx.commit()
        self.inseres = 0

    def process_item(self, item, spider):
        a = ItemAdapter(item)
        try:
            self.cx.execute(
                "INSERT OR IGNORE INTO actions (libelle,cours,variation,volume,isin) "
                "VALUES (:libelle,:cours,:variation,:volume,:isin)",
                dict(a),
            )
            self.inseres += self.cx.execute("SELECT changes()").fetchone()[0]
            self.cx.commit()
        except sqlite3.Error as e:
            spider.logger.error(f"SQLite : {e}")
        return item

    def close_spider(self, spider):
        total = self.cx.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
        spider.logger.info(f"BDD : {self.inseres} nouvelles lignes, {total} actions au total")
        self.cx.close()
