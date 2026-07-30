import scrapy


class MentionItem(scrapy.Item):
    titre = scrapy.Field()
    url = scrapy.Field()
    source = scrapy.Field()
    date_publi = scrapy.Field()
    resume = scrapy.Field()
    score_alerte = scrapy.Field()  # 0=neutre 1=negatif 2=positif
