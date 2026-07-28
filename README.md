# TP Jour 1 — Veille technologique automatisée

**Mohammed MOSLEH** — IPSSI, Mastère Dev, Data & IA — Module Web Scraping, jour 01/05

Scraping des 200 derniers articles du [Blog du Modérateur](https://www.blogdumoderateur.com/)
avec `requests`, `BeautifulSoup4`, export CSV UTF-8 et base SQLite.

> Jour 2 (Selenium — Doctolib & Les Echos) : voir [README_JOUR2.md](README_JOUR2.md).

## Installation

```bash
python -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Utilisation

```bash
python scraper_bdm.py --max 200                 # collecte complète (~7 min)
python scraper_bdm.py --max 200 --no-chapeau    # sans les chapôs (~40 s)
python scraper_bdm.py --max 50 --csv test.csv --db test.db
```

| Option | Défaut | Rôle |
|---|---|---|
| `--max` | 200 | nombre d'articles visés |
| `--csv` | `articles.csv` | fichier CSV de sortie |
| `--db` | `articles.db` | base SQLite de sortie |
| `--no-chapeau` | off | ne visite pas les fiches article |

## Livrables

| Fichier | Contenu |
|---|---|
| `scraper_bdm.py` | scraper principal, exécutable en une commande |
| `articles.csv` | 200 lignes, UTF-8, 5 champs |
| `articles.db` | SQLite, table `articles`, `url` en `UNIQUE` |
| `SELECTEURS.md` | sélecteurs CSS relevés dans DevTools + comparaison des deux sites |
| `scraper_numerama.py` | défi 1 — scraper adapté à un second site |
| `diff_scrapes.py` | défi 2 — comparaison de deux crawls |
| `benchmark.py`, `benchmark_resultats.md` | défi 3 — mesures de throttling |

Résultat du run du 27/07/2026 :

```
300 articles uniques collectés, 200 retenus
CSV : 200 lignes -> articles.csv
SQLite : 200 nouvelles lignes -> articles.db
Terminé : 200 articles en 439.7s
```

Vérifications :

```
CSV lignes: 200            (minimum demandé : 180)
urls uniques: 200
champs vides: titre 0, url 0, date 0, categorie 0, chapeau 0
SELECT COUNT(*) FROM articles; -> 200
dates couvertes : 2026-05-26 -> 2026-07-27
```

## Partie 1 — Cadre légal et éthique

### 1.1 Le scraping de `/feed/` est-il autorisé ?

**Non.** `https://www.blogdumoderateur.com/robots.txt` contient, dans le bloc
`User-agent: *` qui s'applique à notre scraper :

```
User-agent: *
Disallow: /admin$
Disallow: /wp-admin
Disallow: /wp-login.php
Disallow: /?s=
Disallow: /*s=
Disallow: /category/*/*
Disallow: */trackback
Disallow: /feed/
Disallow: /*/feed/
Disallow: /comments
...
```

`Disallow: /feed/` et `Disallow: /*/feed/` interdisent explicitement les flux RSS,
à la racine comme sur n'importe quelle sous-section. Le scraper ne touche donc
aucune URL en `/feed/`.

Deux autres règles ont orienté la conception :

- `Disallow: /category/*/*` — les archives à deux niveaux sous `/category/` sont
  interdites. Les rubriques utilisées ici sont servies à la racine
  (`/web/`, `/ia/`, `/marketing/`, `/social/`, `/tech/`) et leur pagination
  (`/web/page/2/`) ne tombe sous aucune règle `Disallow`.
- Le fichier bloque intégralement (`Disallow: /`) une longue liste d'agents
  agressifs, dont `Python-urllib`, `Wget` et `HTTrack`. Notre User-Agent est un
  identifiant propre et non l'un de ces agents ; il relève du bloc `*`.

### 1.2 Les trois questions avant la première requête

**Ai-je le droit ?** Oui. `robots.txt` autorise les rubriques et leur pagination,
et n'interdit que l'administration WordPress, la recherche interne, les flux et
les commentaires. Les CGU du site n'interdisent pas la consultation automatisée
d'un volume raisonnable à des fins non commerciales. L'usage ici est strictement
pédagogique et les données ne sont pas republiées.

**Est-ce personnel ?** Non. Les cinq champs collectés — titre, URL, date,
catégorie, chapô — sont des métadonnées éditoriales publiques. Aucune donnée à
caractère personnel au sens du RGPD n'est extraite : le nom des auteurs, présent
sur les fiches article, est volontairement exclu du schéma. Aucun cookie, aucun
compte, aucun contenu réservé aux abonnés n'est touché.

**Suis-je discret ?** Oui, sur trois points concrets :

- User-Agent identifiable avec un contact :
  `IPSSI-scraper/1.0 (TP Mastere Dev Data IA; +contact@ipssi.fr)`. L'éditeur peut
  nous joindre ou nous bloquer ciblément plutôt que de subir un trafic anonyme.
- `time.sleep(1.5)` entre chaque requête, soit ~0,67 req/s, très en deçà de ce
  qu'encaisse un site média. Le run complet a fait 220 requêtes en 7 min 20.
- `timeout=10`, `raise_for_status()`, backoff exponentiel sur les 5xx et respect
  du header `Retry-After` sur les 429 : en cas de fragilité du serveur, le
  scraper ralentit au lieu d'insister.

Base juridique : la collecte de données publiques à des fins de recherche et
d'enseignement est licite dans l'UE (directive 2019/790 art. 3-4, et CJUE
*Ryanair* C-30/14 sur les bases non protégées par le droit sui generis), sous
réserve de ne pas contourner de mesure technique et de ne pas porter atteinte au
fonctionnement du site — les deux conditions sont respectées ici.

## Partie 1.3 — Pagination : ce que l'énoncé prévoyait et ce que fait le site

L'énoncé propose de boucler sur `https://www.blogdumoderateur.com/page/N/`.
**Cette boucle ne fonctionne pas** : les pages 2, 3 et 4 renvoient un HTTP 200
avec exactement le même contenu que la page d'accueil.

Mesure faite avant d'écrire le scraper :

```
page 1: 200  cards=41  dup_prev=0   dates 2021-11-17..2026-07-27
page 2: 200  cards=41  dup_prev=41  dates 2021-11-17..2026-07-27
page 3: 200  cards=41  dup_prev=41  dates 2021-11-17..2026-07-27
page 4: 200  cards=41  dup_prev=41  dates 2021-11-17..2026-07-27
total uniques : 41
```

Deux problèmes se cumulent :

1. **La home ne pagine pas.** C'est une page d'accueil WordPress statique :
   `/page/N/` ne déclenche aucune requête d'archive et resert la même vue. Suivre
   l'énoncé produirait un CSV de 200 lignes contenant 41 articles répétés — un
   livrable qui passe la checklist « ≥ 180 lignes » tout en étant faux.
2. **La home n'est pas chronologique.** Elle mélange l'actualité du jour avec des
   contenus permanents : les dates vont de 2021 à 2026 sur la même page. Ce ne
   sont donc pas « les 200 derniers articles ».

**Solution retenue.** Le scraper parcourt les cinq rubriques du menu
(`web`, `ia`, `marketing`, `social`, `tech`), qui elles paginent réellement et
sont triées par date décroissante :

```
web page 1: 200  cards=21  dup=0  dates 2026-07-02..2026-07-23
web page 2: 200  cards=15  dup=0  dates 2026-06-11..2026-07-02
web page 3: 200  cards=15  dup=0  dates 2026-05-20..2026-06-10
uniques : 51
```

Les résultats des cinq rubriques sont fusionnés dans un dictionnaire indexé par
URL (déduplication : un article classé dans deux rubriques n'est compté qu'une
fois), triés par date décroissante, puis tronqués à `--max`. On obtient bien les
200 articles les plus récents, couvrant ici du 26/05/2026 au 27/07/2026.

Environ 15 articles par page de rubrique, contre 41 cartes sur la home.

## Choix techniques

**Sélecteurs.** Ceux de l'énoncé (`h2.post-title a`, `.cat-links a`,
`.entry-summary`) ne renvoient plus rien sur le HTML servi aujourd'hui. Le détail
du relevé DevTools et des sélecteurs réellement utilisés est dans
[SELECTEURS.md](SELECTEURS.md). Point le plus piégeux : le site sert **deux
gabarits de carte**, et dans l'un d'eux le lien est porté par le `<a>` *parent*
de l'`<article>`, pas par un enfant — d'où le repli
`card.select_one("header a[href]") or card.find_parent("a", href=True)`.

**Chapô.** `.entry-summary` n'existe sur aucun listing : les cartes n'affichent
pas de chapô. Il est récupéré sur la fiche article dans `meta[name="description"]`
(repli sur `og:description`), au prix d'une requête par article. C'est ce qui fait
passer le run de 40 s à 7 min ; `--no-chapeau` permet de s'en passer.

**Robustesse.** `get_page()` retente 3 fois avec un backoff exponentiel
(1 s, 2 s, 4 s) sur les timeouts et les 5xx, respecte `Retry-After` sur les 429,
et laisse remonter les 4xx qui sont définitifs. Une rubrique qui répond 404 est
abandonnée sans faire échouer le run.

**Déduplication.** Deux niveaux : en mémoire par URL pendant la collecte, et en
base via `url TEXT NOT NULL UNIQUE` + `INSERT OR IGNORE`. Un second run sur la
même base affiche bien `SQLite : 0 nouvelles lignes`.

**Contraintes de l'énoncé.** `parse_articles()` est écrite en list-comprehension
avec filtre `if`, et les messages de log sont des f-strings.

## Défi 1 — Adapter le scraper à un autre site

Site choisi : **Numerama** (`/actualites/`), actualité tech et sciences — un
domaine que je suis déjà par intérêt personnel, et dont le HTML n'a rien à voir
avec celui du BDM (classes utilitaires Tailwind, cartes `article.card-post`).

`scraper_numerama.py` fait 45 lignes et réutilise `get_page()` et `sauver_csv()`
importées de `scraper_bdm` — aucun copier-coller.

```bash
python scraper_numerama.py     # -> articles_numerama.csv, 20 lignes
```

Les sélecteurs relevés et la comparaison en 3 phrases sont dans
[SELECTEURS.md](SELECTEURS.md). En résumé : l'URL et la date sont **plus simples**
(URL absolue toujours au même endroit, date dans un attribut `data-pub-date` sur
l'`<article>`), la catégorie est **plus difficile** (absente de la carte, il faut
la déduire du chemin de l'URL). Le sélecteur du titre **n'est pas du même type** :
`p.card-post__title a` chez Numerama contre `h3.entry-title` au BDM — cibler un
niveau de titre HTML ne marcherait pas ici.

Piège rencontré : la liste contient des cartes sponsorisées pointant vers
`native.humanoid.fr`. Elles sont filtrées en exigeant `numerama.com` dans le lien.
Autre limite, `/actualites/page/2/` répond 200 mais sans aucune carte — la suite
est chargée en JavaScript, ce qui relève du jour 2 (Selenium).

## Défi 2 — Détecter les nouveautés entre deux crawls

```bash
python scraper_bdm.py --max 200 --no-chapeau --csv articles_run2.csv
python diff_scrapes.py articles_run1.csv articles_run2.csv
```

Résultat des deux crawls du 27/07/2026, espacés d'environ 15 minutes :

```
Nouveaux : 0
Disparus : 0
Stables  : 200
```

Zéro écart, ce qui est le résultat attendu sur un intervalle aussi court et qui
valide au passage la stabilité de l'extraction : deux exécutions indépendantes
produisent exactement le même jeu de 200 URLs.

**Combien d'articles nouveaux en 24 h ?** Plutôt que d'attendre 24 h, la réponse
se lit dans la distribution des dates du corpus déjà collecté (45 jours distincts
couverts, bornes exclues pour éviter les journées tronquées) :

```
articles/jour  moyenne 4,4  médiane 4,0  maximum 10
```

Soit environ **4 à 5 articles par jour** sur les cinq rubriques suivies, avec des
pointes à 10.

**Quel intervalle de crawl ?** Le scraper retient 200 articles, soit à ce rythme
une profondeur d'environ 62 jours d'historique. La fenêtre est donc très large :
même un crawl quotidien ne manquerait rien. La contrainte « ne pas dépasser
1 crawl/heure » est confortable — **un crawl toutes les 6 heures** suffit
largement (au pic de 10 articles/jour, cela représente 2 à 3 articles par crawl,
loin de saturer les 200 lignes retenues), tout en gardant une veille réactive à
une demi-journée près. Descendre sous l'heure n'apporterait rien : on relirait
200 fois le même contenu pour découvrir en moyenne 0,2 article.

## Défi 3 — Benchmark du throttling

Mesures réelles faites avec `benchmark.py` sur les archives `/web/`
(voir [benchmark_resultats.md](benchmark_resultats.md)) :

| Pages | 0.5 s | 1.0 s | 2.0 s |
|-------|-------|-------|-------|
| 2 | 1.4 s | 1.9 s | 2.9 s |
| 5 | 4.3 s | 6.3 s | 10.3 s |
| 10 | 9.1 s | 13.5 s | 22.5 s |

La progression est linéaire et conforme au modèle
`durée ≈ n × latence + (n − 1) × délai`. On en déduit une latence réseau moyenne
d'environ **0,46 s par requête** : sur 10 pages à 2 s, 18 s des 22,5 s mesurées
sont du sommeil volontaire, soit 80 % du temps.

**Au-delà de quel délai 200 articles dépassent-ils 30 minutes ?**
200 articles ≈ 14 pages de rubrique, mais le run complet visite aussi les
200 fiches article pour le chapô, soit ~220 requêtes. Avec
`220 × (0,46 + d) ≤ 1800 s`, on obtient `d ≤ 7,9 s`. **Le seuil est donc d'environ
8 secondes** de délai. Sans les chapôs (14 requêtes seulement), le délai pourrait
monter à plus de 2 minutes sans jamais approcher les 30 minutes — le coût est
entièrement dû à la visite des fiches article, pas à la pagination.

**Politique < 1 req/2 s, combien d'heures pour 500 articles ?**
500 articles avec chapô ≈ 535 requêtes à 2,46 s l'unité = 1 316 s, soit
**environ 22 minutes**. Sans chapô (35 pages), moins de 2 minutes. Même à ce
rythme très prudent, la collecte reste une affaire de minutes, pas d'heures.

**Quel compromis en production ?** Je garderais **1,5 s**, la valeur utilisée ici.
Le raisonnement : le gain de temps entre 1,5 s et 0,5 s est d'environ 3 minutes
sur un run complet — négligeable pour une veille qui tourne en tâche de fond la
nuit — alors que le risque de se faire blacklister par le WAF, lui, n'est pas
négligeable. Le vrai levier de performance n'est pas le délai mais **le nombre de
requêtes** : mettre en cache les chapôs déjà connus supprime à lui seul 90 % du
trafic dès le second run, puisque seuls les ~5 articles du jour sont réellement
nouveaux. Ralentir coûte des minutes, se faire bloquer coûte le projet.

## Checklist de rendu

- [x] `python scraper_bdm.py --max 200` tourne sans crash
- [x] `articles.csv` contient 200 lignes (≥ 180), encodage UTF-8
- [x] `articles.db` : `SELECT COUNT(*) FROM articles;` retourne 200
- [x] `robots.txt` vérifié, User-Agent identifiable, `sleep` de 1,5 s
- [x] README répond aux 3 questions éthiques
- [x] f-string et list-comprehension présents dans le code
- [x] Défis 1, 2 et 3 traités
