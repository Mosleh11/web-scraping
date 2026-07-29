import scrapy


class ActionItem(scrapy.Item):
    libelle = scrapy.Field()
    cours = scrapy.Field()  # float
    variation = scrapy.Field()  # float, en % (ex: -0.53)
    volume = scrapy.Field()  # int
    isin = scrapy.Field()  # cle UNIQUE en base (voir README : symbole Boursorama)
