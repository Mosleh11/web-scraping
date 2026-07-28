# Sélecteurs relevés — jour 2 (Selenium)

Relevés le 28/07/2026 sur les DOM réels, via `driver.execute_script` et
l'inspection des ancêtres des éléments cibles. Comme au jour 1, les sélecteurs
de l'énoncé ne correspondent plus à ce que servent les sites aujourd'hui.

## Doctolib

### Écart avec l'énoncé

| Champ | Sélecteur de l'énoncé | Occurrences | Sélecteur réel |
|---|---|---|---|
| carte | `div[data-test='search-result-card']` | **0** | `div.dl-card` (filtré sur la présence d'un `h2`) |
| nom | `h2, h3, [class*='name']` | ok via `h2` | `h2` de la carte |
| adresse | `[class*='address']` | **0** | ligne du bloc texte précédant le code postal |
| créneaux | `[class*='slot']` | **0** | textes au format `HH:MM` dans la carte |
| type consult. | `[class*='consultation-mode']` | **0** | présence du mot « visio/vidéo » dans le texte |
| url | `a[href*='/praticien/']` | **0** | `a[href*='/<spécialité>/<ville>/']` |

Le site n'expose plus aucun attribut `data-test` sur les cartes : la page ne
compte que 3 `[data-test]` au total, tous sur des icônes. Les classes utiles
sont celles du design system (`dl-card`, `dl-card-content`) et des classes
utilitaires Tailwind (`flex flex-col gap-16`), qui ne décrivent pas le contenu.

### Structure retenue

La carte praticien est un `div.dl-card` contenant un `h2`. Son `innerText` est
régulier, ce qui permet un découpage par lignes plus robuste que des sélecteurs
de classe :

```
ligne 0 : Dr Delphine MIOULET          -> nom
ligne 1 : Cardiologue                  -> spécialité
ligne 2 : 21 Rue François Garcin       -> rue
ligne 3 : 69003 Lyon                   -> code postal + ville
ligne 4 : Conventionné secteur 2       -> optionnel
puis    : agenda (jours, créneaux ou tirets), « Prochain RDV le … »
```

### Deux pièges

**`.text` de Selenium renvoie du vide hors viewport.** Les 20 cartes sont dans
le DOM après scroll, mais seules celles rendues à l'écran ont un `.text`
non vide. Le premier relevé donnait 1 seul `h2` non vide sur 20. L'extraction
passe donc par `execute_script` et `innerText`, qui lit le DOM indépendamment
du rendu à l'écran.

**Le conteneur apparaît avant son contenu.** `div.dl-card` existe dans le DOM
avant que React n'y injecte le nom du praticien. Attendre `presence_of_element_located`
sur `div.dl-card` rend la main trop tôt et l'extraction renvoie des cartes vides.
`selecteur_carte()` attend donc la condition utile — *une carte qui possède un
`h2`* — et non la simple présence du conteneur.

## Les Echos

### Structure

```
carte     : article                       (dédupliqué par href)
titre     : h3 (ou h2), badge PREMIUM retiré du texte
url       : premier a[href] de l'article
premium   : [data-testid="subscribe-badge"] dont le texte vaut "PREMIUM"
rubrique  : meta[property="article:section"] de la fiche
chapô     : meta[name="description"] de la fiche
heure     : meta[property="article:published_time"] de la fiche
```

### Trois pièges

**Les classes CSS sont inutilisables.** Le site est en styled-components :
`class="sc-19z4l96-2 jmiLnY"`. Ces hash sont régénérés à chaque build, donc un
sélecteur qui s'appuie dessus casse à la prochaine mise en production. Les
seules ancres stables sont la balise `article`, le niveau de titre, le `href`
et l'attribut `data-testid`.

**Les `<article>` sont imbriqués.** Le bloc « une » est un `article` qui contient
lui-même d'autres `article` pointant vers le même lien : 41 balises pour 39
articles distincts. La déduplication se fait sur l'URL.

**Le badge est à l'intérieur du `<h3>`.** Sans traitement, le titre ressort en
`"L'industrie à l'épreuve du feu \nPREMIUM"`. Le texte du badge est retiré du
titre avant enregistrement.

**Le chapô et l'heure ne sont pas sur la une.** Seule la carte principale
affiche « Mis à jour il y a 34 minutes » ; les autres n'ont ni chapô ni heure.
Les deux champs viennent des balises `meta` de la fiche article, lisibles sans
franchir le paywall — une navigation supplémentaire par article.
