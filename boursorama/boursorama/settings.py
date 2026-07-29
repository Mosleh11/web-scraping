BOT_NAME = "boursorama"

SPIDER_MODULES = ["boursorama.spiders"]
NEWSPIDER_MODULE = "boursorama.spiders"

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
    "boursorama.pipelines.CleanPipeline": 100,
    "boursorama.pipelines.ValidationPipeline": 200,
    "boursorama.pipelines.SQLitePipeline": 300,
}

FEEDS = {
    "actions.json": {"format": "json", "encoding": "utf-8", "overwrite": True, "indent": 2},
}
FEED_EXPORT_FIELDS = ["libelle", "cours", "variation", "volume", "isin"]

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
