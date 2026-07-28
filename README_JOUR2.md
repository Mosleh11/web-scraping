# TP Jour 2 — Selenium : Doctolib & Les Echos

**Mohammed MOSLEH** — IPSSI, Mastère Dev, Data & IA — Module Web Scraping, jour 02/05

Pilotage d'un navigateur réel : bannière cookies, `WebDriverWait`, scroll,
mode headless, screenshot automatique en cas d'échec.

## Installation

```bash
pip install -r requirements.txt     # ajoute selenium==4.46.0 au jour 1
```

Selenium Manager télécharge chromedriver tout seul : rien à installer à la main.
Testé avec Chrome 142 sur Windows 11.

## Utilisation

```bash
python doctolib_scraper.py                                   # -> doctolib.json
python doctolib_scraper.py --specialite dentiste --ville paris --visible
python lesechos_scraper.py --limite 15                       # -> lesechos.json
python lesechos_scraper.py --benchmark                       # headless vs visible
python defi_cookies.py && python defi_injection.py           # défi 1
python defi_antibot.py                                       # défi 2
```

## Livrables

| Fichier | Contenu |
|---|---|
| `selenium_utils.py` | briques communes : driver, cookies, attentes, screenshots |
| `doctolib_scraper.py` | TD 2.1 — 10 praticiens, 5 champs |
| `doctolib.json` | 10 fiches ostéopathes Paris (≥ 5 demandés) |
| `lesechos_scraper.py` | TD 2.2 — articles à la une, diagnostic requests, benchmark |
| `lesechos.json` | 15 articles, 5 champs, aucun champ vide (≥ 10 demandés) |
| `benchmark_headless.json` | mesures headless vs visible |
| `screenshots/` | capture d'un échec réel + 4 captures anti-bot |
| `SELECTEURS_JOUR2.md` | relevé DOM des deux sites |
| `defi_cookies.py`, `defi_cookies.json` | défi 1 — inventaire des cookies |
| `defi_injection.py`, `defi_injection.json` | défi 1 — validation de la stratégie 2 |
| `defi_antibot.py`, `defi_antibot.json` | défi 2 — empreinte du driver |

## Pourquoi Selenium et pas requests ?

### Les Echos : requests est bloqué au niveau réseau

Le diagnostic de l'étape 1 est lancé à chaque exécution de `lesechos_scraper.py` :

```
requests / UA scraper honnete   -> {'status': 403, 'octets': 369, 'titres': 0}
requests / UA Chrome            -> {'status': 403, 'octets': 369, 'titres': 0}
```

Ce n'est pas le cas de figure décrit dans l'énoncé (« coquille HTML vide, données
injectées en JS »). Le serveur renvoie un **403 Akamai « Access Denied »** de
369 octets, avant même de servir la page. Et le 403 tombe **aussi avec un
User-Agent Chrome parfaitement crédible** : le blocage ne porte donc pas sur la
chaîne User-Agent mais sur l'empreinte TLS/HTTP du client Python, qui ne
ressemble pas à celle d'un vrai navigateur.

Conclusion : Selenium n'est pas ici un confort pour exécuter du JS, c'est la
seule façon d'obtenir une réponse. Un vrai Chrome produit la bonne poignée de
main TLS et la page arrive (1,5 Mo au lieu de 369 octets).

### Doctolib : contenu injecté en React

Cas classique du cours : la coquille arrive, puis React peuple la liste. Les
`div.dl-card` apparaissent avant même que les noms de praticiens y soient
injectés — d'où l'attente sur une condition métier plutôt que sur la présence
d'un conteneur (voir `SELECTEURS_JOUR2.md`).

## Le résultat le plus utile du TP : headless ≠ invisible

Mesure faite sur Les Echos, même machine, même code, seule l'option change :

| Configuration | Résultat |
|---|---|
| Chrome visible | page servie (1 506 129 octets) |
| Chrome `--headless=new` | **403 Access Denied** (293 octets) |
| Chrome `--headless=new` + `--user-agent=` Chrome normal | page servie (1 506 129 octets) |

Chrome headless annonce `HeadlessChrome/142.0.0.0` dans son User-Agent, et
Akamai bloque cette chaîne. Une seule ligne d'option corrige le problème :

```python
opts.add_argument(f"--user-agent={UA_CHROME}")
```

C'est pour cette raison que `make_driver()` force systématiquement l'User-Agent.
Sans cette ligne, le TD 2.2 est infaisable en headless, et l'erreur est
trompeuse : on croit à un problème de sélecteur alors que la page n'est jamais
arrivée. Le défi 2 confirme la cause côté empreinte (ligne `HEADCHR_UA`).

## Gain headless mesuré

`python lesechos_scraper.py --benchmark` — 3 répétitions par configuration :

| Configuration | Total (driver + page) | Page seule |
|---|---|---|
| visible | 3,93 s | 2,46 s |
| headless | 3,04 s | 1,68 s |
| **gain** | **× 1,29** | **× 1,46** |

L'énoncé annonce « gain ~2-3x en headless », et le cours « headless −30 % ».
**Mes mesures ne retrouvent pas le 2-3x** : ×1,46 sur le temps de page, ×1,29
en incluant le démarrage du driver. Le chiffre du cours (−30 %, soit ×1,43) est
en revanche cohérent avec ce que j'observe.

Deux raisons à l'écart avec l'énoncé :

1. Le démarrage de Chrome (~1,4 s) est incompressible et identique dans les deux
   modes. Il dilue le gain : plus la page est rapide, plus le ratio total tend
   vers 1.
2. Les images sont déjà désactivées dans les deux modes via
   `profile.managed_default_content_settings.images = 2`. Le cours attribue
   −50 % à ce réglage : ce gain-là est donc déjà pris dans les deux mesures, et
   ne peut plus apparaître comme un avantage du headless.

Le vrai intérêt du headless n'est pas la vitesse mais l'exécution sans écran
(serveur, CI, tâche planifiée) et l'absence de fenêtres qui volent le focus.

## Bannière cookies — les 3 stratégies

`selenium_utils.accepter_cookies()` implémente la **stratégie 1** avec une
cascade de sélecteurs, du plus précis au plus générique :

```python
BOUTONS_COOKIES = [
    (By.ID, "didomi-notice-agree-button"),                 # Didomi (Doctolib)
    (By.CSS_SELECTOR, "button#onetrust-accept-btn-handler"),  # OneTrust
    (By.XPATH, "//button[contains(., 'Tout accepter') or contains(., 'Accepter')]"),
]
```

Doctolib utilise Didomi : le bouton porte l'`id` `didomi-notice-agree-button`,
donc `By.ID` suffit et l'XPath sur le texte n'est qu'un filet. Les Echos ne
présente pas de bannière bloquante dans notre parcours — la fonction le signale
(`Aucune banniere cookies detectee`) sans faire échouer le run.

La **stratégie 2** (injection de cookie) est documentée dans le défi 1, qui
identifie les deux cookies exacts à reproduire. La **stratégie 3** (profil
persistant) n'a pas été retenue : elle mélange l'état de plusieurs runs, ce qui
rend le comportement du scraper non reproductible d'une exécution à l'autre.

## WebDriverWait plutôt que time.sleep

Aucun `time.sleep()` fixe dans le flux principal des deux scrapers. Le point le
moins évident est le scroll : l'énoncé propose `time.sleep(1.5)` entre chaque
défilement. `scroll_jusqu_a_stabilite()` attend plutôt une **condition** — que
le compteur d'éléments ait augmenté — et s'arrête dès que le nombre n'évolue
plus :

```python
WebDriverWait(driver, 4).until(lambda d: d.execute_script(compteur_js, *args) > avant)
```

Le seul `time.sleep` restant est dans `defi_antibot.py`, sur bot.sannysoft.com :
c'est une page de test statique sans élément d'arrivée à attendre.

## Screenshot automatique en cas d'échec

`attendre_presence()` et `selecteur_carte()` capturent l'écran avant de lever
l'exception. Vérifié sur un échec réel provoqué volontairement :

```bash
python doctolib_scraper.py --specialite specialite-inexistante-xyz --ville lyon
# -> Screenshot : screenshots\doctolib_erreur.png
# -> RuntimeError: Aucun selecteur de carte ne fonctionne : ['div.dl-card', ...]
```

La capture `screenshots/doctolib_erreur.png` montre que Doctolib a **redirigé
vers sa page d'accueil** (barre de recherche vide, « Vivez en meilleure santé »)
au lieu de servir une page de résultats. C'est exactement l'intérêt du
screenshot : sans lui, l'exception « aucun sélecteur ne fonctionne » laisse
croire à des sélecteurs cassés, alors que la vraie cause est une redirection —
deux diagnostics opposés qui se corrigent différemment.

## Cadre légal

**Doctolib.** `robots.txt` n'interdit pas les pages de listing par spécialité et
ville (`/osteopathe/paris`). En revanche il interdit explicitement
`/*availabilities*` et `/search_results/*.json` — c'est-à-dire les endpoints qui
servent les disponibilités. Le scraper **ne requête aucun de ces endpoints** :
il lit uniquement ce que la page rend. Aucune donnée personnelle de patient
n'est touchée ; les noms de praticiens et adresses de cabinet sont des données
professionnelles publiques, publiées par les praticiens eux-mêmes à fin de prise
de rendez-vous.

**Les Echos.** Le bloc `User-agent: *` n'interdit que `/internal` et
`/recherche`. La page d'accueil et les articles sont autorisés. Seuls les
chapôs (balises `meta`, prévues pour l'indexation) sont collectés : **aucun
contenu payant n'est extrait**, et le flag `premium` sert justement à marquer ce
qui reste derrière le paywall. Le fichier bloque par ailleurs nommément une
longue liste de crawlers IA et commerciaux ; notre agent n'en fait pas partie,
mais cela indique une politique restrictive assumée — le volume collecté reste
donc volontairement faible (15 articles, une exécution).

**Volumétrie.** Les deux scrapers font une poignée de requêtes par exécution
(1 page de listing + 15 fiches pour Les Echos). Aucune boucle de crawl massif,
donc aucun besoin de throttling agressif comme au jour 1.

## Défi 1 — Cookie forensics

`python defi_cookies.py` compare le cookie jar avant et après le clic « Tout
accepter », sur Doctolib puis sur Maiia (autre plateforme de rendez-vous).

Précision de méthode : `driver.get_cookies()` **ne renvoie que les cookies du
domaine courant**, ce qui donnerait une fausse réponse à la question sur les
cookies tiers. Le script passe donc par CDP,
`driver.execute_cdp_cmd("Network.getAllCookies")`, qui voit tout le jar comme
DevTools > Application.

### Doctolib — 8 cookies après acceptation

| Cookie | Domaine | Durée | Taille | Rôle |
|---|---|---|---|---|
| `didomi_token` | `.doctolib.fr` | 183 j | 444 o | consentement Didomi, JWT base64 |
| `euconsent-v2` | `.doctolib.fr` | 183 j | 62 o | chaîne de consentement IAB TCF v2 |
| `__cf_bm` | `.doctolib.fr` | < 1 j | 220 o | Cloudflare bot management |
| `_doctolib_session` | `www.doctolib.fr` | session | 438 o | session applicative |
| `ssid` / `esid` | `www.doctolib.fr` | 396 j / session | 23-24 o | identifiants de suivi first-party |
| `locale` | `www.doctolib.fr` | 92 j | 2 o | langue |
| `utm_b2b` | `.doctolib.fr` | < 1 j | 35 o | attribution de campagne |

**Résultat contre-intuitif : aucun cookie de tracking tiers.** Après « Tout
accepter », avec images activées et en fenêtre visible (donc sans blocage de ma
part), les 15 cookies observés appartiennent tous à Doctolib. Le seul cookie
cross-domaine est `__cf_bm` sur `.doctolib.com` — Cloudflare, même opérateur, pas
un annonceur. Les 3 cookies tiers de tracking demandés par l'énoncé n'existent
pas ici. C'est cohérent avec le statut de Doctolib : plateforme de santé, où le
partage publicitaire est juridiquement très contraint.

### Le cookie à injecter pour la stratégie 2

```python
driver.get("https://www.doctolib.fr/")
driver.add_cookie({"name": "euconsent-v2", "domain": ".doctolib.fr",
                   "value": "CQoD2oAQoD2oAAHABBENCpFgAAAAAAAAAAAAAAAAAAAA.IAAA.YAAAAAAAAAAA"})
driver.add_cookie({"name": "didomi_token", "domain": ".doctolib.fr", "value": "<jeton>"})
driver.refresh()
```

`euconsent-v2` porte la chaîne TCF, `didomi_token` l'état interne du CMP.
`defi_injection.py` vérifie lesquels sont réellement nécessaires :

| Cookies injectés | Bannière encore affichée ? |
|---|---|
| aucun | oui |
| `euconsent-v2` seul | oui |
| `euconsent-v2` + `didomi_token` | **non** |

Les deux sont donc requis : avec `euconsent-v2` seul, Didomi ne se considère pas
initialisé et réaffiche la bannière. C'est ce qui rend la stratégie 2 plus
robuste que le clic — elle ne dépend ni du libellé du bouton, ni du délai
d'apparition de la bannière — mais aussi plus fragile dans le temps, puisque le
jeton finit par expirer (183 jours ici).

### Comparaison avec Maiia

Les cookies de consentement **ne portent pas du tout le même nom** : Maiia
utilise `tarteaucitron` (365 j) au lieu du couple Didomi. Le reste du jar est
très différent : `datadome` (365 j, protection anti-bot DataDome), quatre
cookies Dynatrace (`dtCookie`, `dtPC`, `dtSa`, `rxVisitor`) et six cookies F5
`TS*`. 13 cookies contre 8, dont 10 déposés à la première visite — soit avant
tout consentement explicite. Un scraper ne peut donc pas réutiliser tel quel le
code de gestion de bannière d'un site à l'autre : c'est précisément pour ça que
`BOUTONS_COOKIES` est une liste ordonnée et non une constante.

## Défi 2 — Empreinte anti-bot du driver

`python defi_antibot.py` teste 4 configurations sur bot.sannysoft.com et compare
les 31 lignes à verdict. Screenshots dans `screenshots/antibot_*.png`.

Seules 4 lignes changent de verdict d'une configuration à l'autre :

| Ligne | brut | stealth | headless sans UA | headless avec UA |
|---|---|---|---|---|
| `WebDriver (New)` | **ROUGE** | VERT | VERT | VERT |
| `HEADCHR_UA` | VERT | VERT | **ROUGE** | VERT |
| `User Agent (Old)` | VERT | VERT | **ROUGE** | VERT |
| `CHR_MEMORY` | VERT | VERT | **ROUGE** | VERT |

**Quels champs passent de rouge à vert ?** Un seul : `WebDriver (New)`, qui teste
`navigator.webdriver`. Les deux options `--disable-blink-features=AutomationControlled`
et `excludeSwitches: ["enable-automation"]` le font passer de `present (failed)`
à `missing (passed)`.

**Le champ webdriver est-il encore détecté en stealth ?** Non — ni `WebDriver (New)`,
ni `WebDriver Advanced`, ni `SELENIUM_DRIVER` ne signalent quoi que ce soit. Sur
ce détecteur, le driver est indiscernable d'un Chrome normal.

**Quels champs deviennent rouges en headless ?** Trois, et ils ont tous la même
cause racine : la chaîne `HeadlessChrome` dans le User-Agent (`HEADCHR_UA`,
`User Agent (Old)`) et l'absence de `window.performance.memory` (`CHR_MEMORY`).
Forcer un User-Agent normal remet les trois au vert. C'est exactement le
mécanisme qui explique le 403 des Echos en headless : le blocage se joue sur le
User-Agent, pas sur une détection sophistiquée.

Ces options restent des réglages de configuration Chrome, appliqués sur des
pages que `robots.txt` autorise — pas un contournement de CAPTCHA ni de paywall.

## Défi 3 — Robustesse face aux changements de site

Le TP demande de relancer le scraper 3 jours après. **Ce délai n'est pas écoulé
au moment du rendu** : je ne peux donc pas répondre au « combien de sélecteurs
ont changé en 3 jours ? » sans inventer un chiffre. Ce que je peux mesurer, en
revanche, c'est le décalage entre les sélecteurs de l'énoncé (écrits il y a
quelques mois) et le DOM d'aujourd'hui — même phénomène, échelle de temps plus
longue.

Résultat : **5 des 6 sélecteurs Doctolib de l'énoncé ne renvoient plus rien**
(tableau complet dans `SELECTEURS_JOUR2.md`), dont le sélecteur de carte lui-même,
`div[data-test='search-result-card']`, qui donne 0 occurrence.

Le mécanisme de fallback est donc implémenté et actif :

```python
CARTES_CANDIDATES = [
    "div.dl-card",                        # observé le 28/07/2026
    "div[data-test='search-result-card']",  # sélecteur de l'énoncé
    "article",                            # filet générique
]
```

`selecteur_carte()` essaie chaque candidat et retient le premier qui trouve des
cartes réellement porteuses d'un `h2`, en signalant le repli dans les logs. Le
même principe s'applique aux champs : `trouver_adresse()` ne cherche pas une
classe CSS mais la ligne qui précède un code postal, et `trouver_nom()` retombe
sur la première ligne du bloc. Ces règles structurelles survivent à un
changement de classes, là où `[class*='address']` — déjà cassé — ne survit pas.

Quand la cascade échoue entièrement, l'échec est explicite et documenté par un
screenshot, plutôt que silencieux avec un JSON vide.

## Limite assumée : les créneaux horaires

Sur `cardiologue/lyon` (l'exemple de l'énoncé), **aucun praticien n'affiche de
créneau** : la grille ne contient que des tirets et un « Prochain RDV le
14 janvier 2027 ». Ce n'est pas un bug d'extraction — la spécialité est
saturée à Lyon. Vérifié en changeant de cible : sur `osteopathe/paris` et
`medecin-generaliste/marseille`, 2 praticiens sur 10 exposent bien leurs
créneaux (`["11:00", "13:00", "10:00"]`).

La cible par défaut est donc `osteopathe/paris`, pour que le champ
`prochains_creneaux` soit réellement démontré. Un champ supplémentaire
`prochain_rdv` a été ajouté : c'est l'information que Doctolib affiche quand il
n'y a pas de créneau proche, et la perdre reviendrait à exporter une carte vide.
Aller chercher les créneaux manquants supposerait d'appeler les endpoints
`/availabilities` — que `robots.txt` interdit explicitement.

## Checklist avant rendu

- [x] `doctolib.json` : 10 praticiens (≥ 5) avec les 5 champs
- [x] `lesechos.json` : 15 articles (≥ 10) avec les 5 champs, aucun champ vide
- [x] `WebDriverWait` utilisé, aucun `time.sleep()` fixe dans le flux principal
- [x] Screenshot capturé en cas d'échec, vérifié sur un échec réel
- [x] README : pourquoi Selenium et pas requests, gain headless mesuré
- [x] Défis 1, 2 et 3 traités
