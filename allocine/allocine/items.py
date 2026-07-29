import scrapy


class FilmItem(scrapy.Item):
    titre = scrapy.Field()
    annee = scrapy.Field()
    realisateur = scrapy.Field()
    note_presse = scrapy.Field()  # float ou None
    note_spectateurs = scrapy.Field()  # float ou None
    url = scrapy.Field()
