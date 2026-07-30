"""Spider de veille OSINT : mentions d'une cible dans des flux RSS.

    scrapy crawl rss_spider -L INFO
    scrapy crawl rss_spider -a cible="BNP Paribas" -L INFO
"""

import unicodedata

import scrapy

from veille.items import MentionItem

# Listes calibrees par defi1_calibration.py : exactitude 33 % -> 67 % sur le
# corpus reellement collecte. Les 3 derniers mots de chaque liste sont les
# ajouts issus de la lecture des articles.
MOTS_NEGATIFS = [
    "fraude", "amende", "condamne", "condamnation", "scandale", "plainte",
    "liquidation", "faillite", "perquisition", "accuse", "enquete", "proces",
    "sanction", "greve", "licenciement", "polemique", "recul", "chute",
    "vigilance", "fait appel", "profiteurs",
]
# "benefice" a ete retire : sur une cible petroliere, un benefice record est
# presque toujours raconte comme un scandale (3 faux positifs sur 5).
MOTS_POSITIFS = [
    "croissance", "record", "acquisition", "innovation",
    "nomination", "partenariat", "expansion", "investissement", "contrat",
    "hausse", "succes", "lancement", "resultats en hausse",
    "approuve", "atout", "lance",
]

# Flux "une" des medias : demandes par l'enonce. Ils donnent une image du
# bruit de fond mediatique, mais ne contiennent presque jamais la cible.
FLUX_UNE = [
    "https://www.lemonde.fr/rss/une.xml",
    "https://www.lesechos.fr/rss/rss_une.xml",
    "https://www.lefigaro.fr/rss/figaro_actualites.xml",
    "https://www.bfmtv.com/rss/info/flux-rss/flux-toutes-les-actualites/",
    "https://www.01net.com/feed/",
]

# Flux de recherche cible. Google News interdit /rss/search dans son
# robots.txt : on utilise Bing News, qui l'autorise (voir README_JOUR4).
FLUX_RECHERCHE = "https://www.bing.com/news/search?q={q}&format=RSS&setmkt=fr-FR"


class RssSpider(scrapy.Spider):
    name = "rss_spider"
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 1.0,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "USER_AGENT": "IPSSI-OSINT-veille (+cours@ipssi.fr)",
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 429],
        "DEFAULT_REQUEST_HEADERS": {
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    }

    def __init__(self, cible="TotalEnergies", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cible = cible
        # les termes de recherche : "TotalEnergies" mais aussi "Total"
        self.termes = {cible.lower(), cible.split()[0].lower()}

    async def start(self):
        """Scrapy 2.13+ remplace start_requests() par une coroutine start().

        Sous Scrapy 2.17, definir start_requests() ne leve aucune erreur : la
        methode est simplement ignoree et le crawl se termine avec 0 requete.
        """
        urls = FLUX_UNE + [FLUX_RECHERCHE.format(q=self.cible.replace(" ", "+"))]
        for url in urls:
            yield scrapy.Request(url, callback=self.parse, errback=self.erreur_flux,
                                 dont_filter=True)

    def erreur_flux(self, failure):
        """Un flux mort ne doit pas faire tomber la veille entiere."""
        self.logger.warning(f"Flux injoignable : {failure.request.url} "
                            f"({failure.value.__class__.__name__})")

    @staticmethod
    def _sans_accents(texte: str) -> str:
        """Les listes de mots-cles sont ecrites sans accents, la presse non.

        Sans cette normalisation, "condamne" ne matche jamais "condamne" avec
        accent aigu, ni "enquete" le mot accentue : tous les articles
        ressortaient au score 0.
        """
        decompose = unicodedata.normalize("NFKD", texte)
        return "".join(c for c in decompose if not unicodedata.combining(c)).lower()

    def score(self, texte: str) -> int:
        plat = self._sans_accents(texte)
        neg = sum(1 for m in MOTS_NEGATIFS if m in plat)
        pos = sum(1 for m in MOTS_POSITIFS if m in plat)
        return 1 if neg > pos else (2 if pos > neg else 0)

    def parse(self, response):
        entrees = response.xpath("//item | //*[local-name()='entry']")
        retenues = 0

        for entree in entrees:
            titre = (entree.xpath("title/text() | *[local-name()='title']/text()")
                     .get("") or "").strip()
            resume = (entree.xpath("description/text() | *[local-name()='summary']/text()")
                      .get("") or "").strip()

            texte = f"{titre} {resume}".lower()
            if not any(t in texte for t in self.termes):
                continue

            url = (entree.xpath("link/text() | *[local-name()='link']/@href")
                   .get("") or "").strip()
            date_pub = (entree.xpath("pubDate/text() | *[local-name()='published']/text()")
                        .get("") or "").strip()

            retenues += 1
            yield MentionItem(
                titre=titre,
                url=url,
                source=response.url.split("/")[2],
                date_publi=date_pub,
                resume=resume[:300],
                score_alerte=self.score(texte),
            )

        self.logger.info(f"{response.url.split('/')[2]} : {retenues} mentions "
                         f"de '{self.cible}' sur {len(entrees)} entrees")
