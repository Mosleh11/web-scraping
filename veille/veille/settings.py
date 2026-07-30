BOT_NAME = "veille"

SPIDER_MODULES = ["veille.spiders"]
NEWSPIDER_MODULE = "veille.spiders"

USER_AGENT = "IPSSI-OSINT-veille (+cours@ipssi.fr)"
ROBOTSTXT_OBEY = True

# Sans cet en-tete, Bing News sert la meme URL en anglais : la veille
# francophone remontait des depeches en anglais et aucun mot-cle ne matchait.
DEFAULT_REQUEST_HEADERS = {
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
}

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
    "veille.pipelines.CleanPipeline": 100,
    "veille.pipelines.ValidationPipeline": 200,
    "veille.pipelines.SQLitePipeline": 300,
}

FEEDS = {
    "mentions.csv": {"format": "csv", "encoding": "utf-8", "overwrite": True},
}
FEED_EXPORT_FIELDS = ["date_publi", "source", "score_alerte", "titre", "url", "resume"]

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
