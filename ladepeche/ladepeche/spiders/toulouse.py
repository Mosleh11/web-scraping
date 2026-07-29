"""Defi 1 - actualite locale de Toulouse (La Depeche du Midi).

    scrapy crawl toulouse -L INFO
"""

import scrapy

from ladepeche.items import ArticleLocalItem


class ToulouseSpider(scrapy.Spider):
    name = "toulouse"
    allowed_domains = ["ladepeche.fr"]
    start_urls = ["https://www.ladepeche.fr/communes/toulouse,31555/"]

    def parse(self, response):
        articles = response.css("article")
        self.logger.info(f"{len(articles)} blocs article sur la page")
        for bloc in articles:
            lien = bloc.css("h2 a::attr(href)").get()
            if not lien:
                continue
            yield ArticleLocalItem(
                # le titre est reparti sur plusieurs noeuds : 'h2 a ::text'
                # (avec l'espace) descend dans les enfants, 'h2 a::text' non.
                titre=" ".join(bloc.css("h2 a ::text").getall()),
                url=response.urljoin(lien),
                date="",  # rempli par CleanPipeline depuis l'URL
            )
