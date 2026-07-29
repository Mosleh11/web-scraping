"""Spider AlloCine : top des meilleurs films, liste -> fiche detail.

    scrapy crawl films -L INFO
    scrapy crawl films -a max_pages=5 -L INFO
"""

import scrapy

from allocine.items import FilmItem


class FilmsSpider(scrapy.Spider):
    name = "films"
    allowed_domains = ["allocine.fr"]
    start_urls = ["https://www.allocine.fr/film/meilleurs/"]

    def __init__(self, max_pages=20, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 10 films par page : 20 pages = les 200 films demandes
        self.max_pages = int(max_pages)

    def parse(self, response, page=1):
        liens = response.css("h2.meta-title a::attr(href)").getall()
        self.logger.info(f"page {page} : {len(liens)} films")
        for lien in liens:
            yield response.follow(lien, callback=self.parse_film)

        # 'a.button--right' (enonce) ne renvoie rien, et le bloc .pagination
        # n'existe que sur la page 1, ou il saute de 10 a 20 puis 30. On ne
        # peut donc pas enchainer de page en page : on programme depuis la
        # premiere page toutes les suivantes, sur le motif '?page=N' verifie
        # en scrapy shell.
        if page == 1:
            for n in range(2, self.max_pages + 1):
                yield response.follow(
                    f"/film/meilleurs/?page={n}",
                    callback=self.parse,
                    cb_kwargs={"page": n},
                )

    def parse_film(self, response):
        notes = {}
        for bloc in response.css(".rating-item"):
            textes = [t.strip() for t in bloc.css("::text").getall() if t.strip()]
            if len(textes) >= 2:
                notes[textes[0]] = textes[1]

        # 'De' precede le nom du realisateur dans le bloc direction
        direction = [t.strip() for t in response.css(".meta-body-direction ::text").getall() if t.strip()]
        realisateur = direction[1] if len(direction) > 1 else ""

        infos = [t.strip() for t in response.css(".meta-body-info ::text").getall() if t.strip()]

        yield FilmItem(
            titre=response.css(".titlebar-title::text").get(""),
            annee=infos[0] if infos else "",
            realisateur=realisateur,
            note_presse=notes.get("Presse"),
            note_spectateurs=notes.get("Spectateurs"),
            url=response.url,
        )
