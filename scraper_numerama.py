"""Defi 1 - scraper minimal adapte a Numerama (actualites tech/sciences).

Reutilise get_page() et sauver_csv() de scraper_bdm sans copier-coller.

Usage :
    python scraper_numerama.py
"""

from scraper_bdm import get_page, sauver_csv

URL = "https://www.numerama.com/actualites/"
CIBLE = 20


def categorie_depuis_url(url: str) -> str:
    """Numerama n'affiche pas la rubrique sur la carte : elle est dans l'URL."""
    morceaux = [m for m in url.split("/") if m]
    return morceaux[2] if len(morceaux) > 3 else ""


def parse_numerama(soup) -> list[dict]:
    return [
        {
            "titre": card.select_one("p.card-post__title a").get_text(strip=True),
            "url": card.select_one("p.card-post__title a")["href"],
            "date": (card.get("data-pub-date") or "")[:10],
            "categorie": categorie_depuis_url(card.select_one("p.card-post__title a")["href"]),
            "chapeau": "",
        }
        for card in soup.select("article.card-post")
        # le lien externe filtre les cartes sponsorisees (native.humanoid.fr)
        if card.select_one("p.card-post__title a")
        and "numerama.com" in card.select_one("p.card-post__title a")["href"]
    ]


if __name__ == "__main__":
    articles = parse_numerama(get_page(URL))[:CIBLE]
    print(f"{len(articles)} articles recuperes sur Numerama")
    for a in articles[:3]:
        print(f"  {a['date']} [{a['categorie']}] {a['titre'][:60]}")
    sauver_csv(articles, "articles_numerama.csv")
