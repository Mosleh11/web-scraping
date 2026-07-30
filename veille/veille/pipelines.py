import re
import sqlite3

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

DDL = """CREATE TABLE IF NOT EXISTS mentions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    titre        TEXT NOT NULL,
    url          TEXT UNIQUE,
    source       TEXT,
    date_publi   TEXT,
    resume       TEXT,
    score_alerte INTEGER DEFAULT 0,
    scraped_at   TEXT DEFAULT CURRENT_TIMESTAMP
)"""

RE_BALISES = re.compile(r"<[^>]+>")


class CleanPipeline:
    """Les resumes RSS contiennent souvent du HTML : on le retire."""

    def process_item(self, item, spider):
        a = ItemAdapter(item)
        a["titre"] = re.sub(r"\s+", " ", a.get("titre") or "").strip()
        resume = RE_BALISES.sub(" ", a.get("resume") or "")
        a["resume"] = re.sub(r"\s+", " ", resume).strip()[:300]
        a["source"] = (a.get("source") or "").strip()
        return item


class ValidationPipeline:
    def process_item(self, item, spider):
        a = ItemAdapter(item)
        if not a.get("titre") or not a.get("url"):
            raise DropItem(f"Mention incomplete : {dict(a)}")
        return item


class SQLitePipeline:
    def open_spider(self, spider):
        self.cx = sqlite3.connect("veille.db")
        self.cx.execute(DDL)
        self.cx.commit()
        self.inseres = 0

    def process_item(self, item, spider):
        a = ItemAdapter(item)
        try:
            self.cx.execute(
                "INSERT OR IGNORE INTO mentions "
                "(titre,url,source,date_publi,resume,score_alerte) VALUES(?,?,?,?,?,?)",
                (a["titre"], a.get("url", ""), a.get("source", ""),
                 a.get("date_publi", ""), a.get("resume", ""), a.get("score_alerte", 0)),
            )
            self.inseres += self.cx.execute("SELECT changes()").fetchone()[0]
            self.cx.commit()
        except sqlite3.Error as e:
            spider.logger.error(f"SQLite : {e}")
        return item

    def close_spider(self, spider):
        total = self.cx.execute("SELECT COUNT(*) FROM mentions").fetchone()[0]
        repartition = dict(self.cx.execute(
            "SELECT score_alerte, COUNT(*) FROM mentions GROUP BY score_alerte"))
        spider.logger.info(
            f"[OSINT] {self.inseres} nouvelles mentions, {total} en base "
            f"| repartition des scores {repartition}")
        self.cx.close()
