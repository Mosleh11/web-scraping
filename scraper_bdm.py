"""Scraper des derniers articles du Blog du Moderateur.

Usage :
    python scraper_bdm.py --max 200

Produit articles.csv (UTF-8) et articles.db (SQLite, URL UNIQUE).
"""

import argparse
import csv
import sqlite3
import time

import requests
from bs4 import BeautifulSoup

DOMAINE = "https://www.blogdumoderateur.com"

HEADERS = {
    "User-Agent": "IPSSI-scraper/1.0 (TP Mastere Dev Data IA; +contact@ipssi.fr)",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
}

# La home ne pagine pas (voir README) : on passe par les archives de rubrique,
# qui sont paginees et triees par date decroissante.
RUBRIQUES = ["web", "ia", "marketing", "social", "tech"]

DELAI = 1.5
CHAMPS = ["titre", "url", "date", "categorie", "chapeau"]


def get_page(url: str, tries: int = 3) -> BeautifulSoup:
    """GET avec timeout, retry et backoff exponentiel sur les erreurs temporaires."""
    for attempt in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 10))
                print(f"429 sur {url} - attente {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return BeautifulSoup(r.text, "lxml")
        except requests.Timeout:
            print(f"Timeout {attempt + 1}/{tries} sur {url}")
            time.sleep(2**attempt)
        except requests.HTTPError as e:
            if e.response.status_code < 500:
                raise
            print(f"HTTP {e.response.status_code} - retry {attempt + 1}/{tries}")
            time.sleep(2**attempt)
    raise RuntimeError(f"Echec apres {tries} tentatives : {url}")


def _url_carte(card) -> str:
    """L'URL est soit sur un <a> parent (cartes serp), soit dans le header."""
    lien = card.select_one("header a[href]") or card.find_parent("a", href=True)
    if lien is None:
        return ""
    href = lien["href"]
    return DOMAINE + href if href.startswith("/") else href


def _texte(card, selecteur: str, limite: int = 300) -> str:
    noeud = card.select_one(selecteur)
    return noeud.get_text(strip=True)[:limite] if noeud else ""


def parse_articles(soup: BeautifulSoup) -> list[dict]:
    return [
        {
            "titre": _texte(card, "h3.entry-title", 300),
            "url": _url_carte(card),
            "date": card.select_one("time[datetime]")["datetime"][:10],
            "categorie": _texte(card, "span.favtag", 80),
            "chapeau": "",
        }
        for card in soup.select("article.post")
        if card.select_one("h3.entry-title") and card.select_one("time[datetime]")
    ]


def scrape_rubrique(rubrique: str, max_articles: int) -> list[dict]:
    """Parcourt /<rubrique>/page/N/ jusqu'a epuisement ou quota atteint."""
    articles = []
    page = 1
    while len(articles) < max_articles:
        url = f"{DOMAINE}/{rubrique}/" if page == 1 else f"{DOMAINE}/{rubrique}/page/{page}/"
        try:
            soup = get_page(url)
        except requests.HTTPError as e:
            print(f"{rubrique} page {page} : HTTP {e.response.status_code}, arret")
            break
        nouveaux = [a for a in parse_articles(soup) if a["url"]]
        if not nouveaux:
            print(f"{rubrique} : plus d'articles page {page}, arret")
            break
        articles.extend(nouveaux)
        print(f"{rubrique} page {page} => {len(nouveaux)} articles | sous-total={len(articles)}")
        page += 1
        time.sleep(DELAI)
    return articles


def ajouter_chapeaux(articles: list[dict]) -> None:
    """Le chapo n'existe pas sur les listings : on le lit sur la fiche article."""
    for i, a in enumerate(articles, 1):
        try:
            soup = get_page(a["url"])
            meta = soup.select_one('meta[name="description"]') or soup.select_one(
                'meta[property="og:description"]'
            )
            a["chapeau"] = (meta.get("content", "") if meta else "")[:300]
        except (requests.RequestException, RuntimeError) as e:
            print(f"Chapo indisponible ({e.__class__.__name__}) : {a['url']}")
        if i % 25 == 0:
            print(f"Chapos : {i}/{len(articles)}")
        time.sleep(DELAI)


def scrape_all(max_articles: int = 200, avec_chapeau: bool = True) -> list[dict]:
    """Agrege les rubriques, deduplique sur l'URL, garde les plus recents."""
    par_url = {}
    quota = max_articles // len(RUBRIQUES) + 10
    for rubrique in RUBRIQUES:
        for a in scrape_rubrique(rubrique, quota):
            par_url.setdefault(a["url"], a)

    articles = sorted(par_url.values(), key=lambda a: a["date"], reverse=True)[:max_articles]
    print(f"{len(par_url)} articles uniques collectes, {len(articles)} retenus")

    if avec_chapeau:
        ajouter_chapeaux(articles)
    return articles


def sauver_csv(articles: list[dict], chemin: str = "articles.csv") -> None:
    with open(chemin, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS, extrasaction="ignore")
        w.writeheader()
        w.writerows(articles)
    print(f"CSV : {len(articles)} lignes -> {chemin}")


DDL = """
CREATE TABLE IF NOT EXISTS articles (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    titre      TEXT NOT NULL,
    url        TEXT NOT NULL UNIQUE,
    date       TEXT,
    categorie  TEXT,
    chapeau    TEXT,
    scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""


def sauver_sqlite(articles: list[dict], chemin: str = "articles.db") -> None:
    with sqlite3.connect(chemin) as cx:
        cx.execute(DDL)
        inserted = 0
        for a in articles:
            try:
                cx.execute(
                    "INSERT OR IGNORE INTO articles (titre,url,date,categorie,chapeau) "
                    "VALUES (:titre,:url,:date,:categorie,:chapeau)",
                    a,
                )
                inserted += cx.execute("SELECT changes()").fetchone()[0]
            except sqlite3.Error as e:
                print(f"Erreur SQLite sur {a['url']} : {e}")
        cx.commit()
    print(f"SQLite : {inserted} nouvelles lignes -> {chemin}")


def main():
    p = argparse.ArgumentParser(description="Scraper Blog du Moderateur")
    p.add_argument("--max", type=int, default=200, help="Nb max d'articles")
    p.add_argument("--csv", default="articles.csv")
    p.add_argument("--db", default="articles.db")
    p.add_argument("--no-chapeau", action="store_true", help="Ne pas visiter les fiches article")
    args = p.parse_args()

    t0 = time.time()
    print(f"Demarrage - cible : {args.max} articles")
    articles = scrape_all(args.max, avec_chapeau=not args.no_chapeau)
    sauver_csv(articles, args.csv)
    sauver_sqlite(articles, args.db)
    print(f"Termine : {len(articles)} articles en {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
