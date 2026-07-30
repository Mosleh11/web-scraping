# ETHIQUE.md — TP Jour 4 (OSINT)

**Mohammed MOSLEH** — IPSSI, Mastère Dev, Data & IA

Les trois questions du cours (*ai-je le droit ? est-ce personnel ? suis-je
discret ?*) posées pour chacun des trois TD, avec les décisions concrètes
prises dans le code.

---

## TD 4.1 — Empreinte d'un domaine

### Ai-je le droit ?

**Oui pour les sources retenues, non pour celle de l'énoncé.**

| Source | robots.txt | Décision |
|---|---|---|
| WHOIS | protocole port 43, pas de robots | utilisée |
| Certificat TLS du serveur | hors périmètre de robots.txt | utilisée |
| `sitemap.xml` | vérifié avant chaque appel | utilisée si autorisé |
| `robots.txt` de la cible | lecture du fichier lui-même | utilisée |
| **crt.sh** | `User-agent: * / Disallow: /` | **écartée** |

crt.sh interdit l'intégralité de son site à tous les robots. Interroger son API
JSON contredirait la règle n°4 du TP (« robots.txt respecté pour chaque
cible »). `sous_domaines_crtsh()` est écrite comme le demande l'énoncé mais
vérifie `robots.txt` et refuse par défaut ; il faut passer `--crtsh`
explicitement pour forcer, et le rapport indique alors clairement le statut.

À la place, les sous-domaines viennent du **certificat TLS que le serveur cible
présente lui-même** pendant la poignée de main — exactement ce que reçoit un
navigateur. Aucun tiers n'est interrogé, aucune directive n'est contournée.
Sur `wikipedia.org`, cette méthode remonte 41 noms.

Sur le fond, WHOIS et les journaux de certificats sont des registres publics par
construction : la transparence des certificats existe précisément pour être
auditée. Aucune authentification n'est franchie, aucun port n'est scanné, aucune
vulnérabilité n'est testée — on ne fait que lire ce que le serveur publie.

### Est-ce personnel ?

**Non, et une donnée a été volontairement exclue.**

Le rapport contient des données techniques : IP, registrar, dates, serveurs de
noms, en-têtes HTTP, noms de sous-domaines. `python-whois` renvoie aussi, selon
les extensions, le nom, l'adresse postale, l'e-mail et le téléphone du titulaire
— **ces champs ne sont pas repris dans le rapport**. C'est une donnée à
caractère personnel au sens du RGPD dès que le titulaire est une personne
physique, et elle n'est d'aucune utilité pour une évaluation d'exposition
technique.

Base légale retenue : intérêt légitime (art. 6.1.f), finalité documentée =
évaluation d'exposition technique dans un cadre pédagogique, aucune conservation
au-delà du rendu, aucune rediffusion.

### Suis-je discret ?

- User-Agent identifiable avec contact : `IPSSI-OSINT (+cours@ipssi.fr)`
- `time.sleep(1.0)` entre chaque étape (`DELAI = 1.0`)
- `timeout=10` sur toutes les requêtes, exceptions capturées et consignées dans
  le rapport plutôt que propagées
- **Volume total : 8 requêtes HTTP pour un domaine complet.** C'est de l'OSINT
  passif : on ne balaye aucun port, on n'énumère aucun sous-domaine par force
  brute, on ne teste aucune authentification.

### Bonus — que révèle la liste des sous-domaines sur l'architecture interne ?

Sur `wikipedia.org`, les 41 noms du certificat dessinent la carte des projets
Wikimedia (`*.m.wikibooks.org`, `*.m.wikidata.org`, `*.m.wikinews.org`…) : le
préfixe `m.` systématique révèle une architecture à domaines mobiles séparés,
et le fait qu'un seul certificat les couvre tous indique une terminaison TLS
mutualisée en frontal plutôt qu'un certificat par service.

Le classement automatique (`classer_sous_domaines`) cherche les motifs
`preprod`, `staging`, `recette`, `dev`, `test`, `vpn`, `git`, `jenkins`… Zéro
sur Wikipedia — ce qui est le résultat attendu d'une infrastructure mature. Un
`jenkins.` ou un `staging.` dans un certificat public trahirait à la fois
l'existence d'un environnement hors production et son nom d'hôte exact, soit un
point d'entrée souvent moins durci que la production.

---

## TD 4.2 — Cartographie d'une entité publique

### Ai-je le droit ?

**Oui, avec une substitution de source.**

| Source | Statut | Décision |
|---|---|---|
| API Recherche d'entreprises (`api.gouv.fr`) | service public ouvert, sans clé | utilisée |
| Wikipedia (`fr.wikipedia.org/wiki/…`) | autorisé par robots.txt (vérifié) | utilisée |
| **Google News RSS** | `Disallow: /` sauf quelques chemins ; `/rss/search` **non listé** | **écartée** |
| Bing News RSS | `/news/search` autorisé (vérifié) | utilisée |

Le robots.txt de `news.google.com` n'autorise que `/`, `/home`, `/topics/`,
`/publications/`, `/stories/`, `/swg/` et `/about`. L'URL `/rss/search?q=…` de
l'énoncé n'entre dans aucune de ces exceptions. La veille presse passe donc par
Bing News, dont le robots.txt autorise `/news/search`. La vérification est faite
dans le code par `robots_autorise()` avant chaque appel, pas seulement à la main.

Le registre SIRENE est public par nature : la loi impose la publicité des
immatriculations d'entreprises, c'est le principe même du registre du commerce.

### Est-ce personnel ?

**Non.** La fiche porte sur une **personne morale** (TotalEnergies SE,
SIREN 542051180). Les données du RCS relatives à une société ne sont pas des
données personnelles. L'adresse retenue est celle du **siège social**, pas un
domicile.

Deux garde-fous appliqués :

- l'API SIRENE expose aussi des dirigeants nommément — ces champs ne sont **pas**
  repris dans la fiche ;
- de l'infobox Wikipedia, on garde les champs d'entreprise (forme juridique,
  création, chiffres) ; les noms de personnes qui y figurent (fondateurs,
  dirigeants) ne sont pas extraits séparément ni indexés.

Si la cible avait été une personne physique, le TP changerait de nature : il
faudrait une base légale distincte et l'intérêt légitime ne suffirait
probablement pas.

### Suis-je discret ?

- User-Agent identifiable, `DELAI = 1.0` entre chaque source
- 3 sources, ~6 requêtes au total pour une fiche complète
- L'API SIRENE est paginée par 10 : le code s'arrête **dès qu'il a trouvé** la
  correspondance exacte (page 2 pour TotalEnergies) au lieu d'aspirer les
  64 pages de résultats.

---

## TD 4.3 — Veille automatisée (Scrapy)

### Ai-je le droit ?

**Oui.** `ROBOTSTXT_OBEY = True` est actif dans `settings.py` **et** dans les
`custom_settings` du spider : Scrapy vérifie lui-même chaque flux et filtre ce
qui est interdit, sans que j'aie à y penser.

Les flux RSS sont publiés **pour être consommés par des agrégateurs** : c'est
leur raison d'être. Seuls les titres, chapôs et liens sont stockés — pas le
corps des articles, qui est protégé par le droit d'auteur. La base sert à
repérer des mentions et à pointer vers la source, pas à se substituer à elle.

Un cas concret : `lesechos.fr/rss/rss_une.xml` renvoie un **403** derrière son
CDN. Le flux n'est pas interdit par robots.txt, mais le serveur refuse. Le
spider consigne l'échec via `errback` et continue — il ne cherche pas à
contourner le refus (ni UA de navigateur, ni proxy).

### Est-ce personnel ?

**Non.** Les items contiennent titre, URL, source, date, chapô et un score
calculé. Les noms de journalistes ne sont pas extraits, les noms de personnes
cités dans les titres ne sont ni isolés ni indexés — ils restent dans le texte
du titre, tel que publié.

**Le score d'alerte mérite une réserve.** Attribuer automatiquement une étiquette
« négatif » à un article est un traitement qui peut porter à conséquence si la
cible est une personne, ou si le résultat sert à une décision (crédit, embauche,
rupture de contrat). Ici la cible est une entreprise cotée, le score est un tri
de lecture pour un humain, et sa fiabilité mesurée est de **64 %** (voir défi 1
dans le README) — insuffisante pour automatiser quoi que ce soit. C'est écrit
noir sur blanc pour éviter qu'on lui fasse dire plus qu'il ne peut.

### Suis-je discret ?

- `DOWNLOAD_DELAY = 1.0` + `RANDOMIZE_DOWNLOAD_DELAY = True`
- `AUTOTHROTTLE_ENABLED = True` (délai adaptatif selon la latence serveur)
- `CONCURRENT_REQUESTS_PER_DOMAIN = 2`
- `RETRY_TIMES = 3` sur 5xx et 429 uniquement — jamais sur un 4xx définitif
- User-Agent `IPSSI-OSINT-veille (+cours@ipssi.fr)`
- **6 requêtes par exécution.** Une veille se relance périodiquement, pas en
  boucle : la déduplication par `UNIQUE(url)` fait qu'un second passage
  n'insère que le nouveau.

---

## Récapitulatif des écarts assumés par rapport à l'énoncé

| Ce que demande l'énoncé | Pourquoi je m'en écarte | Ce que je fais |
|---|---|---|
| `crt.sh` pour les sous-domaines | `Disallow: /` — contredit la règle 4 du TP | certificat TLS du serveur cible |
| Google News RSS | `/rss/search` non autorisé | Bing News RSS (`/news/search` autorisé) |
| `api.annuaire-entreprises.data.gouv.fr` | le domaine ne résout plus | `recherche-entreprises.api.gouv.fr` |
| WHOIS complet | champs nominatifs = RGPD | dates, registrar, NS uniquement |
| `fr.wikipedia.org/w/api.php` (défi 3) | `/w/` interdit par robots.txt | `api.wikimedia.org` (autorisé) |

Aucun de ces écarts ne réduit le périmètre du TP : chaque source écartée est
remplacée par une source équivalente et autorisée.
