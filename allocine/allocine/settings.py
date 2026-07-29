BOT_NAME = "allocine"

SPIDER_MODULES = ["allocine.spiders"]
NEWSPIDER_MODULE = "allocine.spiders"

# L'UA Scrapy par defaut recolte un 403 sur AlloCine : un UA identifiable
# avec un contact passe (verifie en scrapy shell, voir SELECTEURS_JOUR3.md).
USER_AGENT = "IPSSI-scraper (+contact@ipssi.fr)"

ROBOTSTXT_OBEY = True

DOWNLOAD_DELAY = 1.0
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0

RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 429]

ITEM_PIPELINES = {
    "allocine.pipelines.ValidationPipeline": 100,
    "allocine.pipelines.CleanPipeline": 200,
}

FEEDS = {
    "films.json": {"format": "json", "encoding": "utf-8", "overwrite": True, "indent": 2},
    "films.csv": {"format": "csv", "encoding": "utf-8", "overwrite": True},
}

FEED_EXPORT_FIELDS = ["titre", "annee", "realisateur", "note_presse", "note_spectateurs", "url"]

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
