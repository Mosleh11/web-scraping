BOT_NAME = "ladepeche"

SPIDER_MODULES = ["ladepeche.spiders"]
NEWSPIDER_MODULE = "ladepeche.spiders"

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

ITEM_PIPELINES = {"ladepeche.pipelines.CleanPipeline": 100}

FEEDS = {"articles_toulouse.csv": {"format": "csv", "encoding": "utf-8", "overwrite": True}}
FEED_EXPORT_FIELDS = ["date", "titre", "url"]

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
