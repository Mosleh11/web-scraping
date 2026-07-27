# Sélecteurs CSS relevés dans DevTools

Relevés le 27/07/2026 sur les deux sites. Les sélecteurs d'un site changent avec
ses refontes : ce document date donc l'état observé au moment du TP.

## Blog du Modérateur

### Écart avec l'énoncé

L'énoncé donne les sélecteurs suivants, qui ne correspondent plus au HTML servi
aujourd'hui. Vérification faite sur la page d'accueil et sur `/web/` :

| Champ | Sélecteur de l'énoncé | Occurrences trouvées | Sélecteur réel |
|---|---|---|---|
| titre | `h2.post-title a` | 0 | `h3.entry-title` |
| url | `h2.post-title a[href]` | 0 | voir ci-dessous (deux gabarits) |
| date | `time[datetime]` | 44 | `time[datetime]` (inchangé) |
| catégorie | `.cat-links a` | 17 (menu, pas les cartes) | `span.favtag` |
| chapô | `.entry-summary` | 0 | absent des listings |

Le sélecteur de carte `article.post` de l'énoncé est en revanche correct.

### Sélecteurs retenus

```
carte     : article.post
titre     : h3.entry-title              -> .get_text(strip=True)
url       : header a[href]  OU  <a> parent de la carte
date      : time[datetime]              -> ['datetime'][:10]
catégorie : span.favtag                 -> .get_text(strip=True)
chapô     : meta[name="description"] sur la fiche article
```

### Deux gabarits de carte

Le site sert deux structures selon l'emplacement, et l'URL ne se récupère pas au
même endroit dans les deux cas :

1. **Carte « serp »** — la balise `<article>` est *enveloppée* par un
   `<a class="content-serp-card">`. Le lien est donc sur le **parent**, il n'y a
   aucun `<a>` à l'intérieur de la carte.
2. **Carte « d-flex »** — le lien est *à l'intérieur*, dans
   `header.entry-header > a`.

D'où le repli dans `_url_carte()` :

```python
lien = card.select_one("header a[href]") or card.find_parent("a", href=True)
```

Une extraction qui ne cherche l'`<a>` qu'à l'intérieur de la carte perd
silencieusement toutes les cartes du premier gabarit.

### Chapô

`.entry-summary` n'existe sur aucune page de listing : les cartes affichent
uniquement image, catégorie, date et titre. Le chapô est récupéré sur la fiche
article, dans `meta[name="description"]` (avec `og:description` en repli), ce qui
coûte une requête supplémentaire par article. L'option `--no-chapeau` permet de
sauter cette étape.

## Numerama (défi 1)

Site choisi : [numerama.com/actualites](https://www.numerama.com/actualites/) —
actualité tech et sciences. `robots.txt` n'interdit que `/search/`, les feeds et
les endpoints API ; `/actualites/` est autorisé.

```
carte     : article.card-post
titre     : p.card-post__title a        -> .get_text(strip=True)
url       : p.card-post__title a        -> ['href'] (déjà absolue)
date      : attribut data-pub-date de <article>  -> [:10]
catégorie : déduite du 1er segment de l'URL (/sciences/, /tech/, /vroom/…)
```

### Comparaison en 3 phrases

L'URL est plus simple à extraire que sur le BDM : elle est toujours absolue et
toujours au même endroit, alors que le BDM impose de gérer deux gabarits dont un
où le lien est sur le parent de la carte. La date est plus simple aussi, elle est
portée par un attribut `data-pub-date` directement sur l'`<article>`, sans
descendre dans le DOM. En revanche la catégorie est plus difficile : Numerama ne
l'affiche pas sur la carte, il faut la déduire du chemin de l'URL, et le titre
n'est pas dans un `<h2>`/`<h3>` mais dans un `<p class="card-post__title">` — ce
n'est donc pas le même type de sélecteur que sur le BDM (`h3.entry-title`), un
sélecteur basé sur le niveau de titre HTML ne fonctionnerait pas ici.

### Limite observée

`/actualites/page/2/` répond 200 mais ne contient aucune carte : la suite de la
liste est chargée en JavaScript. Les 25 articles de la première page suffisent
pour les 20 demandés ; aller plus loin relèverait du jour 2 (Selenium).
