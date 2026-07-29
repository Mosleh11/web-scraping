import scrapy


class ArticleLocalItem(scrapy.Item):
    titre = scrapy.Field()
    url = scrapy.Field()
    date = scrapy.Field()
