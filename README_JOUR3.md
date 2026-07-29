# TP Jour 3 — Scrapy : AlloCiné & Boursorama

**Mohammed MOSLEH** — IPSSI, Mastère Dev, Data & IA — Module Web Scraping, jour 03/05

Trois projets Scrapy complets : items, pipelines, settings, spiders avec follow
des liens, Feed Exports et pipeline SQLite.

## Installation

```bash
pip install -r requirements.txt     # ajoute scrapy==2.17.0
```

## Utilisation

```bash
cd allocine    && scrapy crawl films -L INFO        # -> films.json + films.csv
cd boursorama  && scrapy crawl cac -L INFO          # -> bourse.db + actions.json
cd ladepeche   && scrapy crawl toulouse -L INFO     # défi 1 -> articles_toulouse.csv
python benchmark_scrapy.py                          # défi 2
```

Options : `scrapy crawl films -a max_pages=5`, `scrapy crawl cac -a max_pages=2`.

## Livrables

| Fichier | Contenu |
|---|---|
| `allocine/` | projet complet : `items.py`, `pipelines.py`, `settings.py`, `spiders/films.py` |
| `allocine/films.json` · `films.csv` | **198 films**, 6 champs, types castés |
| `boursorama/` | 2ᵉ projet, avec `SQLitePipeline` |
| `boursorama/bourse.db` | **80 actions**, table `actions`, `UNIQUE(isin)` |
| `boursorama/analyse_bourse.sql` · `analyse_bourse.csv` | défi 3 |
| `ladepeche/` | 3ᵉ projet — défi 1, site local |
| `benchmark_scrapy.py` · `benchmark_scrapy.md` | défi 2 |
| `SELECTEURS_JOUR3.md` | validations `scrapy shell` des trois sites |

Résultats des crawls du 29/07/2026 :

```
films        : item_scraped_count 198 | response_received_count 219 | 268 s
cac          : item_scraped_count  93 | 80 lignes en base (13 doublons ignorés)
toulouse     : item_scraped_count  37 | 0 item droppé
```

Vérifications :

```
films.json      : 198 films, 198 URLs uniques, 0 titre/année/réalisateur vide
films.csv       : 198 lignes
bourse.db       : SELECT COUNT(*) -> 80, COUNT(DISTINCT isin) -> 80
                  0 cours, 0 variation, 0 volume à NULL
articles_toulouse.csv : 37 lignes, 0 champ vide
```

## Pourquoi 198 films et pas 200

Le spider parcourt 20 pages × 10 liens = **200 liens émis**, et Scrapy en scrape
198. La différence est visible dans les stats :

```
'dupefilter/filtered': 2,
```

Deux films apparaissent deux fois dans le classement AlloCiné, sur des pages
différentes. Le **Scheduler** les a dédupliqués tout seul : c'est exactement le
travail qu'il faisait à la main au jour 1 avec un `dict` indexé par URL. Ici
c'est gratuit, et ça se lit dans les stats de fin de crawl.

## Ce que `scrapy shell` a permis d'éviter

L'énoncé insiste : shell d'abord, spider ensuite. C'est ce qui a permis de
constater, **avant d'écrire une ligne de spider**, que :

- l'UA Scrapy par défaut prend un **403** sur AlloCiné (l'UA honnête passe) ;
- `a.button--right` (pagination) renvoie `None` ;
- `h1::text` renvoie une chaîne vide ;
- `.meta-body-direction a::text` renvoie `[]` ;
- sur Boursorama, la colonne `cells[3]` de l'énoncé est **le cours d'ouverture**,
  pas le volume.

Le détail complet est dans [SELECTEURS_JOUR3.md](SELECTEURS_JOUR3.md). Les deux
erreurs les plus coûteuses auraient été silencieuses : un volume rempli avec un
prix d'ouverture, et une note spectateurs écrasée par la valeur `--` du bloc
« Mes amis » (le `:last-child` de l'énoncé). Dans les deux cas le crawl se
termine sans erreur, avec des données fausses mais plausibles.

## Ce que `ROBOTSTXT_OBEY = True` a bloqué

Point le plus intéressant du TP côté Boursorama.

Le palmarès est scindé en onglets (Hausses / Baisses) sélectionnés par
`?france_filter[variation]=50001|50002`. En ne collectant que l'URL par défaut,
**toutes les lignes sont des hausses** : la requête « top 5 baisses » du défi 3
renvoie alors les cinq plus *petites hausses*, ce qui n'a aucun sens analytique.

J'ai donc voulu ajouter l'onglet Baisses — et le crawl est revenu vide, avec une
seule réponse (le `robots.txt`). Vérification :

```
RULE: Disallow: /*filter[variation]=*
RULE: Disallow: /*filter%5Bvariation%5D=*
```

Boursorama interdit explicitement les vues filtrées par variation. La forme
non encodée `?france_filter[variation]=50002` passe littéralement le test de
`protego` — mais l'intention du fichier est sans ambiguïté, et l'utiliser
reviendrait à contourner une règle affichée. **Je ne l'ai pas fait.**

La solution retenue respecte à la fois `robots.txt` et l'énoncé : le filtre par
**marché** n'est pas interdit, et `?france_filter[market]=1rPCAC` donne le
**CAC 40** — précisément la cible annoncée par le TP — qui contient de vraies
hausses et de vraies baisses puisqu'il est trié par ordre alphabétique et non par
performance. Le spider part donc de deux URLs autorisées : le CAC 40 et le
palmarès général.

## La colonne `isin` ne contient pas d'ISIN

L'énoncé indique que « le code ISIN est souvent dans l'URL du lien ». Ce n'est
pas le cas : `/cours/1rPATE/` porte `1rPATE`, l'identifiant interne Boursorama.
Recherche menée en shell (détail dans [SELECTEURS_JOUR3.md](SELECTEURS_JOUR3.md)) :
aucune chaîne au format ISIN ISO 6166 dans le HTML, ni sur le listing ni sur la
fiche valeur. Le vrai ISIN d'ALTEN est `FR0000071946` — il n'apparaît nulle part
chez Boursorama.

La table conserve donc le nom de colonne `isin` exigé par le livrable, avec la
contrainte `UNIQUE` qui fonctionne (80 lignes, 80 valeurs distinctes, 13 doublons
inter-pages écartés par `INSERT OR IGNORE`), mais elle est alimentée par
`data-ist`. C'est signalé dans `items.py`, dans le spider et ici : une colonne
nommée `isin` qui contiendrait autre chose sans le dire serait un piège pour
quiconque réutiliserait la base.

## Architecture des projets

**Pipelines chaînés**, dans l'ordre déclaré par `ITEM_PIPELINES` :

- `allocine` : `ValidationPipeline` (100) → `CleanPipeline` (200)
- `boursorama` : `CleanPipeline` (100) → `ValidationPipeline` (200) → `SQLitePipeline` (300)

Le `CleanPipeline` d'AlloCiné fait trois choses : trim des textes, extraction de
l'année par regex depuis `"4 septembre 2024"`, et cast des notes en `float` après
remplacement de la virgule décimale. Résultat vérifiable dans le JSON :
`"annee": 2003` (int), `"note_presse": 3.8` (float), et `null` quand la note
n'existe pas — plutôt qu'une chaîne vide.

Côté Boursorama, le nettoyage numérique doit gérer le formatage français :
`2 820,9305` utilise une **espace fine insécable** (` `) comme séparateur de
milliers. Un simple `.replace(" ", "")` sur l'espace ASCII ne suffit pas et
laisse `float()` échouer.

`ValidationPipeline` lève `DropItem` sur les items sans titre (AlloCiné) ou sans
libellé/identifiant (Boursorama), conformément à la bonne pratique n°4 du cours :
un champ manquant doit faire du bruit, pas passer en silence.

## Cadre légal

`ROBOTSTXT_OBEY = True` dans les trois `settings.py`, `DOWNLOAD_DELAY = 1.0` avec
`RANDOMIZE_DOWNLOAD_DELAY`, `AUTOTHROTTLE_ENABLED = True`, et un User-Agent
identifiable avec adresse de contact.

- **AlloCiné** : `/film/meilleurs/` et les fiches film ne tombent sous aucune
  règle `Disallow` du bloc `*` (qui vise `/rechercher/`, `/ws/*.ashx`, les
  iframes et la régie publicitaire). 219 requêtes pour le crawl complet.
- **Boursorama** : voir ci-dessus — une cible a été abandonnée à cause de
  `robots.txt`.
- **La Dépêche** : `/communes/toulouse,31555/` autorisé ; le fichier n'interdit
  que `/agenda`, `/api/`, `/articles-les-plus/`, `/preview/` et `/recherche`.
  Une seule page, une seule requête.

Aucune donnée personnelle : titres de films, réalisateurs, cotations boursières
et titres de presse sont des données éditoriales ou de marché publiques.

## Défi 1 — Spider sur un site local

Cible : **La Dépêche du Midi, page commune de Toulouse**
(`/communes/toulouse,31555/`). Item à 3 champs (`titre`, `url`, `date`),
`CleanPipeline`, export CSV. 37 articles, aucun champ vide.

**Cinq lignes de comparaison avec AlloCiné.** La structure est *plus simple*
mais *moins prévisible* : une seule page suffit pour dépasser les 20 éléments
demandés, sans pagination ni fiche détail à suivre, alors qu'AlloCiné impose un
crawl à deux niveaux sur 20 pages. En revanche AlloCiné a des classes stables et
sémantiques (`meta-title`, `meta-body-direction`, `rating-item`) tandis que La
Dépêche n'expose qu'un `article > h2 > a` générique, sans aucune classe
exploitable et **sans balise `<time>`**. La date n'existe nulle part dans le
HTML : je l'extrais du chemin de l'URL (`/2026/07/29/`), ce qui est un sélecteur
structurel et non CSS. Le titre demande aussi une astuce, `h2 a ::text` avec
l'espace descendant, parce que `h2 a::text` renvoie du vide. Conclusion : un
gros site éditorial est plus verbeux mais plus documenté par ses classes ; un
site régional est plus léger mais force à s'accrocher à ce qui ne bouge pas —
la balise, le schéma d'URL — plutôt qu'au CSS.

## Défi 2 — Performances de crawl

`python benchmark_scrapy.py`. Deux séries, parce que la première seule ne montre
rien (voir plus bas). Résultats dans [benchmark_scrapy.md](benchmark_scrapy.md).

### Série A — réglages de politesse du TP (10 pages, 100 films)

`DOWNLOAD_DELAY = 1.0` + `AUTOTHROTTLE_ENABLED = True`

| CONCURRENT_REQUESTS | temps (s) | items | items/s | items/responses |
|---|---|---|---|---|
| 1 | 136,5 | 100 | 0,73 | 0,901 |
| 4 | 137,8 | 100 | 0,73 | 0,901 |
| 8 | 133,4 | 100 | 0,75 | 0,901 |
| 16 | 132,8 | 100 | 0,75 | 0,901 |

**Le paramètre n'a aucun effet** : 3 % d'écart entre 1 et 16, soit le bruit de
mesure. C'est logique et c'est le point à retenir : `DOWNLOAD_DELAY` et
`AUTOTHROTTLE` imposent un espacement *par domaine*. Comme tout le crawl tape un
seul domaine, la file est sérialisée à ~1 requête/s quoi qu'on demande. Monter
`CONCURRENT_REQUESTS` à 16 dans ces conditions ne fait qu'agrandir une file
d'attente qui ne se vide pas plus vite.

### Série B — throttling désactivé (3 pages seulement)

`DOWNLOAD_DELAY = 0`, `AUTOTHROTTLE_ENABLED = False`. Volume réduit
volontairement à 33 requêtes par run pour ne pas matraquer AlloCiné.

| CONCURRENT_REQUESTS | temps (s) | items | items/s | gain vs précédent |
|---|---|---|---|---|
| 1 | 2,8 | 30 | 10,73 | — |
| 4 | 1,8 | 30 | 16,92 | × 1,58 |
| 8 | 1,7 | 30 | 17,82 | × 1,05 |
| 16 | 1,6 | 30 | 18,45 | × 1,03 |

**À partir de quelle valeur le gain devient-il négligeable ?** Dès **4**. Le
passage de 1 à 4 fait gagner 58 % ; de 4 à 8, 5 % ; de 8 à 16, 3 %. Au-delà de 4
connexions simultanées, le facteur limitant n'est plus le parallélisme du client
mais la latence du serveur et le temps de parsing local. Les valeurs du TP
(`CONCURRENT_REQUESTS = 4`, `PER_DOMAIN = 2`) sont donc bien choisies.

**Pourquoi AUTOTHROTTLE peut battre une valeur fixe élevée ?** Une valeur fixe
est un pari aveugle : elle ne sait pas si le serveur souffre. AutoThrottle
mesure la latence de chaque réponse et ajuste le délai en continu — si le
serveur ralentit, il espace ; s'il répond vite, il accélère. Une valeur fixe à
16 sur un serveur qui commence à peiner déclenche des 429 et des 5xx, chacun
rejoué jusqu'à `RETRY_TIMES = 3` : le débit *utile* s'effondre pendant qu'on
augmente la charge. AutoThrottle trouve le point d'équilibre au lieu de le
chercher par l'échec.

**Que signifie un ratio `item_scraped_count / response_received_count` bas ?**
Ici il vaut **0,901** : 100 items pour 111 réponses. Les 11 réponses sans item
sont les 10 pages de liste — qui ne produisent que des requêtes, pas des données
— plus le `robots.txt`. Le ratio plafonne donc naturellement autour de
`n_détails / (n_détails + n_listes)`. Un ratio **< 0,5** signifierait que plus
d'une réponse sur deux ne produit rien : sur AlloCiné, cela voudrait dire soit
des fiches film qui échouent au parsing (sélecteur cassé, items droppés par le
pipeline de validation), soit des redirections et des 403 comptés comme réponses.
C'est un signal d'alerte à surveiller à chaque crawl, pas une métrique de
performance.

## Défi 3 — SQL et interprétation financière

Requêtes dans [boursorama/analyse_bourse.sql](boursorama/analyse_bourse.sql),
export complet dans `analyse_bourse.csv`. Base : 80 actions, snapshot du
29/07/2026 vers 14 h 55.

### Top 5 hausses

| Valeur | Variation | Cours |
|---|---|---|
| ALTEN | +19,39 % | 79,75 |
| SOPRA STERIA | +15,51 % | 198,90 |
| KERING | +14,63 % | 287,15 |
| BUREAU VERITAS | +8,05 % | 29,52 |
| ATOS GROUP | +6,45 % | 33,98 |

### Top 5 baisses

| Valeur | Variation | Cours |
|---|---|---|
| HERMES INTL | −11,56 % | 1 499,50 |
| DANONE | −4,76 % | 68,80 |
| ESSILORLUXOTTICA | −2,94 % | 163,70 |
| STMICROELECTRONICS | −2,32 % | 43,45 |
| SCHNEIDER ELECTRIC | −1,91 % | 257,00 |

### Moyenne ou médiane pour les volumes ?

L'énoncé commente sa requête « volume > 2× la médiane » mais écrit `AVG(volume)`.
Les deux ne donnent pas du tout le même résultat :

```
moyenne = 311 711     médiane = 172 947
au-dessus de 2× la moyenne : 5 actions
au-dessus de 2× la médiane : 18 actions
```

La moyenne est tirée vers le haut par quelques très gros volumes, ce qui remonte
le seuil et masque des titres réellement actifs. Sur des volumes boursiers, dont
la distribution est fortement asymétrique, la médiane est la bonne référence.
Le fichier SQL implémente la vraie médiane (`ORDER BY volume LIMIT 1 OFFSET n/2`)
et conserve la version `AVG` en commentaire pour la comparaison.

### Confrontation avec l'actualité du jour

**ALTEN, +19,4 %** — le mouvement s'explique entièrement. Le groupe d'ingénierie
a publié un retour à la croissance organique au 2ᵉ trimestre 2026, avec un chiffre
d'affaires de 1 055,5 M€ (+3,3 %, dont +6,5 % en France), au-dessus des attentes,
et a **relevé ses objectifs annuels**. La presse financière relève le même jour
que le titre signe la plus forte hausse du SBF 120. Ma valeur scrapée (+19,39 %)
est cohérente avec les +20 % rapportés.

**HERMÈS, −11,56 %** — publication des résultats du 1ᵉʳ semestre le matin même :
8,16 Md€ de chiffre d'affaires, +6,1 % à taux de change constants mais seulement
+1,6 % en publié, et surtout une croissance limitée à 2,5 % en Asie-Pacifique
hors Japon. La marge opérationnelle de 41 % dépasse pourtant les attentes : c'est
bien la *dynamique* de croissance, pas la rentabilité, qui a déçu.

Nuance méthodologique importante : les articles parlent d'une baisse de 5 à 8 %,
là où ma base indique −11,56 %. Il n'y a pas de contradiction — **mon crawl est
un instantané intraday** (14 h 55), pas une variation de clôture. Le titre était
au plus bas au moment du scrape et s'est repris ensuite. C'est une limite
structurelle de ce genre de collecte : sans horodatage précis, une variation
boursière n'est pas interprétable. La colonne `scraped_at` de la table
(`DEFAULT CURRENT_TIMESTAMP`) est là pour ça.

## Checklist avant rendu

- [x] `scrapy crawl films` → `films.json` + `films.csv`, 198 films (≥ 50 demandés)
- [x] `scrapy crawl cac` → `bourse.db`, table `actions`, `UNIQUE(isin)` vérifié
      (93 items scrapés → 80 lignes, 13 doublons ignorés)
- [x] `ROBOTSTXT_OBEY = True` dans les trois `settings.py`
- [x] `DOWNLOAD_DELAY = 1.0` dans les trois `settings.py`
- [x] `scrapy shell` utilisé pour valider les sélecteurs avant chaque spider
- [x] `CleanPipeline` : notes castées en float, année en int, trim des textes
- [x] Défis 1, 2 et 3 traités

## Sources (défi 3)

- [Alten : la croissance prend le marché de vitesse, l'action flambe de 20 % — BFM Bourse](https://www.tradingsat.com/alten-FR0000071946/actualites/alten-la-croissance-du-groupe-d-ingenierie-alten-prend-le-marche-de-vitesse-l-action-flambe-de-20-1167693.html)
- [Alten grimpe en Bourse, porté par une croissance supérieure aux attentes — ABC Bourse](https://www.abcbourse.com/marches/alten-grimpe-en-bourse-porte-par-une-croissance-superieure-aux-attentes-et-des_700564)
- [Hermès chute de 8 % après des résultats S1 décevants — Investing.com](https://fr.investing.com/news/stock-market-news/hermes-chute-de-8--apres-des-resultats-s1-decevants-sur-la-croissance-3521523)
- [Hermès croît malgré des vents contraires au Moyen-Orient et en Chine mais son action chute — La Libre](https://www.lalibre.be/dernieres-depeches/2026/07/29/hermes-croit-malgre-des-vents-contraires-au-moyen-orient-et-en-chine-mais-son-action-chute-RXQNNYZRTZFO5HTV7MRJA36MHM/)
