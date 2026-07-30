# TP Jour 4 — OSINT : renseignement en sources ouvertes

**Mohammed MOSLEH** — IPSSI, Mastère Dev, Data & IA — Module Web Scraping, jour 04/05

Réemploi de `requests` + `BeautifulSoup4` (jour 1) et de Scrapy (jour 3) sur
trois cibles publiques : empreinte d'un domaine, fiche d'entité, veille presse.

> Le cours du jour 4 est une révision (matrice de décision, checklist
> prêt-pour-la-prod, 3 ateliers) suivie de l'évaluation. Le TP rendu ici est le
> sujet OSINT distribué en parallèle.

## Installation

```bash
pip install -r requirements.txt   # ajoute python-whois et feedparser
```

## Utilisation

```bash
python td41_domaine.py wikipedia.org                  # -> rapport_domaine.json
python td41_domaine.py ipssi.fr --sortie rapport_domaine_ipssi.json
python td42_entite.py TotalEnergies                   # -> fiche_entite.json

cd veille && scrapy crawl rss_spider -L INFO          # -> mentions.csv + veille.db
cd veille && scrapy crawl rss_spider -a cible="BNP Paribas"

cd veille && python ../defi1_calibration.py           # défi 1
cd veille && python ../defi3_wikipedia.py TotalEnergies   # défi 3
```

## Livrables

| Fichier | Contenu |
|---|---|
| `td41_domaine.py` → `rapport_domaine.json` | WHOIS, en-têtes, TLS, sous-domaines, robots |
| `td42_entite.py` → `fiche_entite.json` | SIREN + infobox Wikipedia + 10 articles |
| `veille/` (Scrapy) → `mentions.csv`, `veille.db` | 12 mentions, `UNIQUE(url)`, score d'alerte |
| `ETHIQUE.md` | les 3 questions pour **chacun** des 3 TD |
| `defi1_calibration.py` | défi 1 — précision mesurée du scoring |
| `rapport_domaine_ipssi.json` | défi 2 — domaine que je connais |
| `defi3_wikipedia.py` | défi 3 — croisement veille / historique Wikipedia |

Résultats des exécutions du 30/07/2026 :

```
rapport_domaine.json  : wikipedia.org, 41 sous-domaines, TLS valide (Let's Encrypt)
fiche_entite.json     : SIREN 542051180, 24 champs d'infobox, 10 articles
veille.db             : 12 mentions, 12 URLs uniques, scores {0:4, 1:3, 2:5}
mentions.csv          : 12 lignes
```

## Quatre sources de l'énoncé sont inutilisables telles quelles

C'est le fil rouge de ce TP. L'énoncé pose comme règle n°4 « robots.txt respecté
pour chaque cible » — et propose ensuite trois sources qui l'interdisent.

### 1. crt.sh interdit tout crawl

```
$ curl https://crt.sh/robots.txt
User-agent: *
Disallow: /
```

Il n'y a pas d'exception : le site entier est interdit. `sous_domaines_crtsh()`
est écrite comme le demande l'énoncé, mais elle **vérifie robots.txt et refuse
par défaut**. Le rapport porte alors la trace de ce choix :

```json
"crtsh": {
  "statut": "non interroge",
  "raison": "robots.txt de crt.sh interdit tout crawl ; relancer avec --crtsh pour forcer",
  "sous_domaines": []
}
```

**Remplacement : le certificat TLS présenté par le serveur cible.** Les noms du
champ `subjectAltName` sont exactement ce qu'un navigateur reçoit en se
connectant. Aucun tiers interrogé, aucune directive contournée, et le résultat
est de même nature — 41 noms sur `wikipedia.org`, contre une liste crt.sh qui
aurait été plus longue mais aussi plus bruitée (certificats expirés, wildcards).

### 2. Google News interdit `/rss/search`

```
User-agent: *
Disallow: /
Allow: /$          Allow: /home$      Allow: /topics/
Allow: /?          Allow: /home?      Allow: /publications/
```

`/rss/search?q=…` n'entre dans aucune exception. **Remplacement : Bing News RSS**,
dont le `robots.txt` autorise `/news/search` — vérifié dans le code par
`robots_autorise()` avant chaque appel, pas seulement à la main.

### 3. L'API SIRENE de l'énoncé n'existe plus

`api.annuaire-entreprises.data.gouv.fr` ne résout plus du tout
(`ConnectionError` au niveau DNS). L'API en service est
`recherche-entreprises.api.gouv.fr/search`, avec `limite=` et non `limit=`.

### 4. `fr.wikipedia.org/w/` est interdit (défi 3)

Le robots.txt de Wikipedia interdit `/w/`, ce qui couvre `api.php` **et**
`rest.php`. Pour lire l'historique des révisions, le défi 3 passe donc par
`api.wikimedia.org`, l'API publique officielle, dont le robots.txt autorise
l'appel.

Le détail source par source est dans [ETHIQUE.md](ETHIQUE.md).

## Deux pièges techniques qui rendaient la veille muette

**`start_requests()` n'existe plus dans Scrapy 2.17.** La méthode a été
remplacée par `async def start()` depuis Scrapy 2.13. Le piège : définir
`start_requests()` ne lève **aucune erreur**. Le spider démarre, se termine
proprement, et affiche `Crawled 0 pages` avec `finish_reason: finished`. Aucune
requête n'est jamais partie. Il n'y a pas de message d'avertissement — seul le
compteur `downloader/request_count` absent des stats met sur la piste.

**Bing servait des résultats en anglais à Scrapy et en français à `requests`.**
Même URL, même `setmkt=fr-FR`, réponses différentes : Bing arbitre sur l'en-tête
`Accept-Language`, que Scrapy n'envoie pas par défaut. Conséquence en cascade :
les 12 mentions ressortaient en anglais, aucun mot-clé français ne matchait, et
tous les scores valaient 0. Correction en trois lignes de `settings.py` :

```python
DEFAULT_REQUEST_HEADERS = {
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
}
```

**Bonus, sur les accents.** Les listes de mots-clés de l'énoncé sont écrites
sans accents (`condamne`, `enquete`, `greve`) alors que la presse écrit
`condamné`, `enquête`, `grève`. Un `in` brut ne matche jamais. Le spider
normalise donc le texte en NFKD avant comparaison.

## Les flux RSS de l'énoncé ne trouvent rien

Les 5 flux « une » demandés par l'énoncé donnent **0 mention** de la cible :

```
www.lemonde.fr  : 0 mentions de 'TotalEnergies' sur 14 entrees
www.lefigaro.fr : 0 mentions de 'TotalEnergies' sur 20 entrees
www.bfmtv.com   : 0 mentions de 'TotalEnergies' sur 30 entrees
www.01net.com   : 0 mentions de 'TotalEnergies' sur 30 entrees
www.lesechos.fr : flux injoignable (HTTP 403 derrière le CDN)
www.bing.com    : 12 mentions de 'TotalEnergies' sur 12 entrees
```

C'est logique : un flux « une » contient l'actualité générale du jour, soit
~94 articles, où une entreprise donnée n'apparaît qu'exceptionnellement. Suivre
l'énoncé produit un `veille.db` vide.

Les 5 flux sont **conservés** — ils mesurent le bruit de fond médiatique et
démontrent le parsing RSS/Atom multi-sources — et un **flux de recherche ciblé**
est ajouté, qui lui garantit des mentions. Les Echos reste dans la liste : son
403 sert de démonstration de l'`errback`, qui journalise l'échec sans faire
tomber le crawl.

## Défi 1 — Calibrer le scoring de sentiment

`cd veille && python ../defi1_calibration.py`

J'ai lu les 12 articles collectés (titre, chapô et meta description de la page
source), puis étiqueté chacun selon qu'il est bon, mauvais ou neutre **pour la
cible**. Le script recalcule les scores avec les deux jeux de mots-clés et
compare aux étiquettes.

### Précision réelle des listes de l'énoncé

```
=== v1 - listes de l'enonce (11 articles etiquetes)
  score=2 (positif ) precision 2/5 =  40%   | rappel 2/3 =  67%
  score=1 (negatif ) precision 1/1 = 100%   | rappel 1/7 =  14%
  exactitude globale : 4/11 = 36%
```

**3 faux positifs sur 5**, tous dus au même mot : `benefice`. Sur une cible
pétrolière, un bénéfice record n'est jamais raconté comme une bonne nouvelle :

- « Carburant : TotalEnergies annonce des milliards de bénéfices… pourquoi les
  prix restent élevés »
- « TotalEnergies engrange des milliards de bénéfices mais vous payez toujours
  autant »
- « TotalEnergies double son bénéfice, porté par les prix élevés liés à la
  guerre »

Les trois sont classés **positifs** par le scoring alors que les trois sont des
mises en cause. Et le rappel négatif de 14 % est encore plus parlant : 6 articles
réellement négatifs sur 7 passent entre les mailles, notamment toute la série sur
le devoir de vigilance.

### Les 6 mots ajoutés

| Ajoutés aux négatifs | Pourquoi |
|---|---|
| `vigilance` | 3 articles sur le contentieux « devoir de vigilance » |
| `fait appel` | l'appel du jugement du 25 juin, répété par 3 sources |
| `profiteurs` | titre « Profiteurs de guerre » |

| Ajoutés aux positifs | Pourquoi |
|---|---|
| `approuve` | décision finale d'investissement sur le champ Cronos |
| `atout` | analyse Figaro sur la diversification géographique |
| `lance` | lancement produit Saft |

Plus une suppression : **`benefice` retiré des positifs**, cause des 3 faux
positifs ci-dessus.

### Après calibration

```
=== v2 - listes calibrees (11 articles etiquetes)
  score=2 (positif ) precision 3/4 =  75%   | rappel 3/3 = 100%
  score=1 (negatif ) precision 3/3 = 100%   | rappel 3/7 =  43%
  exactitude globale : 7/11 = 64%

Gain d'exactitude : +27%
```

L'exactitude passe de 36 % à 64 %, la précision des positifs de 40 % à 75 %, et
le rappel des négatifs triple. Les listes calibrées sont désormais celles du
spider.

**Ce que ça ne corrige pas.** Le rappel négatif plafonne à 43 % : les trois
articles sur les bénéfices restent classés neutres, faute de mot-clé négatif
explicite dans leur titre. Leur charge critique tient à la construction de la
phrase (« *mais* vous payez toujours autant »), pas à un vocabulaire. Aucune
liste de mots ne rattrapera ça — il faudrait un vrai modèle de sentiment, ou
accepter que le score soit un tri de lecture et non un verdict. À 64 %, il fait
gagner du temps à un analyste ; il ne peut pas décider à sa place.

## Défi 2 — OSINT sur un domaine que je connais

Cible : **ipssi.fr**, le domaine de mon école.

```bash
python td41_domaine.py ipssi.fr --sortie rapport_domaine_ipssi.json
```

```
IP                : 81.88.57.68
Serveur           : Apache
HTTPS valide      : False
Sous-domaines     : 0
Entetes manquants : csp, hsts, x_frame_options, x_content_type_options, referrer_policy
robots.txt        : HTTP 404
WHOIS             : AMEN, créé le 2007-06-08, expire le 2027-06-08, NS ns1/ns2.amen.fr
```

**Ce qui surprend.** Je m'attendais à trouver des sous-domaines (intranet,
extranet, plateforme pédagogique) : le certificat n'en expose aucun, et il n'y a
ni `sitemap.xml` ni `robots.txt`. Surtout, `https://ipssi.fr` échoue à la
validation (`unable to get local issuer certificate`) : la chaîne de
certification est incomplète côté serveur. Le site répond en **HTTP simple**,
sans redirection vers HTTPS.

**Le serveur est-il identifié, et est-ce utile à un attaquant ?** Oui,
`Server: Apache` — mais sans numéro de version, ce qui est le bon réglage :
impossible d'aller chercher directement une CVE correspondant à une version
précise. `X-Powered-By` n'est pas divulgué non plus. L'information reste utile à
un attaquant pour orienter ses tentatives (chemins Apache typiques, `.htaccess`),
sans lui livrer de cible immédiate.

**Sous-domaines de préproduction exposés ?** Aucun sur ce domaine. Le risque, s'il
y en avait eu, est précis : un environnement de recette est rarement durci comme
la production — mots de passe faibles, données de test parfois copiées de la
prod, correctifs appliqués en retard — et son nom d'hôte dans un certificat
public le rend trouvable sans aucun effort.

### Ce qu'un auditeur externe apprendrait en 5 minutes

> Le domaine `ipssi.fr` est déposé chez AMEN depuis juin 2007 et renouvelé
> jusqu'en juin 2027, hébergé sur une IP unique servie par un Apache qui masque
> sa version. Le point saillant n'est pas une fuite d'information mais une
> faiblesse de configuration : la chaîne de certification TLS est incomplète, si
> bien qu'un navigateur refuse `https://ipssi.fr`, et le site répond en HTTP en
> clair sans redirection ni HSTS — tout ce qu'un étudiant y saisit circule donc
> sans chiffrement. Aucun des cinq en-têtes de sécurité usuels n'est présent
> (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy), ce qui
> laisse la porte ouverte au clickjacking et au sniffing de contenu. En
> contrepartie, la surface exposée est minimale : aucun sous-domaine dans le
> certificat, pas de préproduction visible, pas de technologie applicative
> divulguée. Le correctif le plus rentable est aussi le plus simple : compléter
> la chaîne de certificats, forcer la redirection HTTPS et ajouter HSTS.

## Défi 3 — Croiser veille et historique Wikipedia

`cd veille && python ../defi3_wikipedia.py TotalEnergies`

```
8 mentions alertantes | 20 revisions Wikipedia

Derniere revision : 2026-07-20 (10 jours)
Periode couverte  : 2026-05-26 -> 2026-07-20

  [1] 2026-07-27 Devoir de vigilance : TotalEnergies fait appel      -> AUCUNE revision depuis
  [1] 2026-07-27 Cinq questions avant un proces qui pourrait...      -> AUCUNE revision depuis
  [1] 2026-07-23 "Profiteurs de guerre" : 5,4 milliards de dollars   -> AUCUNE revision depuis
  ...
8/8 evenements ne sont suivis d'aucune revision
```

**L'événement retenu.** L'article le plus chargé de ma veille est l'appel formé
par TotalEnergies, le 27 juillet, contre le jugement du tribunal judiciaire de
Paris du 25 juin qui lui ordonnait d'intégrer les émissions de CO₂ de ses clients
dans son plan de vigilance. Trois sources le rapportent le même jour (L'Opinion,
La Tribune, Yahoo Actualités).

**Ce que dit l'historique Wikipedia.** La page n'a pas bougé depuis le
**20 juillet**, soit 10 jours avant. L'appel n'y figure pas.

En revanche, le **jugement initial**, lui, y est — ajouté le **27 juin**, deux
jours après la décision du 25 juin, avec ce commentaire de révision :

```
2026-06-27 | /* Engagements de réduction des émissions de GES */
             TotalEnergies va devoir prendre en compte les émissions de CO2 de ses clients
```

**Wikipedia est-il une source OSINT fiable pour la veille temps réel ?**

Non, et le contraste ci-dessus dit précisément pourquoi. Sur la même affaire, le
jugement a été enregistré en 2 jours et l'appel ne l'est toujours pas après 10.
La différence n'est pas la gravité de l'événement mais son caractère
spectaculaire : une condamnation fait un titre, un appel de procédure beaucoup
moins. Wikipedia dépend de la disponibilité d'un contributeur bénévole
intéressé, ce qui produit une couverture en dents de scie — excellente sur les
événements marquants, lacunaire sur le suivi.

Ce qui en fait malgré tout une bonne source OSINT, à condition de savoir pour
quoi : Wikipedia est fiable pour le **contexte stable** (historique, filiales,
dirigeants, chiffres consolidés), pas pour l'**actualité**. La veille presse et
l'encyclopédie sont complémentaires — l'une donne le flux, l'autre le fond —
et les confondre revient à croire qu'une absence de modification signifie qu'il
ne s'est rien passé. Sur mon corpus, ce raisonnement aurait fait manquer les
8 événements de la semaine.

## Checklist avant rendu

- [x] `rapport_domaine.json` : WHOIS + sous-domaines + en-têtes HTTP
- [x] `fiche_entite.json` : SIREN + infobox Wikipedia + 10 articles de presse
- [x] `veille.db` : table `mentions` avec `UNIQUE(url)` et `score_alerte`
- [x] `mentions.csv` exportée par Scrapy (Feed Exports)
- [x] `ETHIQUE.md` : les 3 réponses pour **chacun** des 3 TD
- [x] User-Agent identifiable dans tous les scripts
- [x] `sleep >= 1 s` entre requêtes dans `td41` et `td42` (`DELAI = 1.0`)
- [x] Défis 1, 2 et 3 traités
