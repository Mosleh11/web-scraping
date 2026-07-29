"""Spider Boursorama : palmares des actions francaises.

    scrapy crawl cac -L INFO
    scrapy crawl cac -a max_pages=3 -L INFO
"""

import re

import scrapy

from boursorama.items import ActionItem

# Ordre reel des colonnes releve en scrapy shell :
# 0 Libelle | 1 Dernier | 2 Var. | 3 Ouv | 4 +Haut | 5 +Bas | 6 Vol. | 7 Cap.
COL_COURS = 1
COL_VARIATION = 2
COL_VOLUME = 6
NB_COLONNES_ATTENDU = 8


class CacSpider(scrapy.Spider):
    name = "cac"
    allowed_domains = ["boursorama.com"]
    # robots.txt interdit "/*filter%5Bvariation%5D=*", donc les onglets
    # Hausses / Baisses du palmares sont hors limites (voir README_JOUR3).
    # Le filtre par marche, lui, est autorise : on cible le CAC 40 demande
    # par l'enonce, qui contient de vraies hausses ET de vraies baisses.
    BASE = "https://www.boursorama.com/bourse/actions/palmares/france/"
    start_urls = [
        BASE + "?france_filter%5Bmarket%5D=1rPCAC",  # CAC 40
        BASE,                                        # palmares general
    ]

    def __init__(self, max_pages=4, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)

    def parse(self, response, page=1):
        lignes = response.css("table.c-table tbody tr")
        retenues = 0
        for ligne in lignes:
            cellules = ligne.css("td.c-table__cell")
            # la page contient un second tableau (widget lateral) a 3 colonnes
            if len(cellules) < NB_COLONNES_ATTENDU:
                continue

            def texte(cellule):
                return " ".join(t.strip() for t in cellule.css("::text").getall() if t.strip())

            yield ActionItem(
                libelle=texte(cellules[0].css("a") or cellules[0]),
                cours=texte(cellules[COL_COURS]),
                variation=texte(cellules[COL_VARIATION]),
                volume=texte(cellules[COL_VOLUME]),
                # Boursorama n'expose aucun ISIN : data-ist est son identifiant
                # interne, stable et unique par valeur (voir README).
                isin=ligne.attrib.get("data-ist", ""),
            )
            retenues += 1

        self.logger.info(f"page {page} : {retenues} actions retenues sur {len(lignes)} lignes")

        if page < self.max_pages:
            # les liens ont la forme /page-3?france_filter%5Bvariation%5D=50002 :
            # un endswith ne suffit pas, le numero est suivi de la query string
            motif = re.compile(rf"/page-{page + 1}(\?|$)")
            suivant = next(
                (h for h in response.css(".c-pagination a::attr(href)").getall() if motif.search(h)),
                None,
            )
            if suivant:
                yield response.follow(suivant, callback=self.parse, cb_kwargs={"page": page + 1})
