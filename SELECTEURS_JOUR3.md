# Sélecteurs relevés — jour 3 (Scrapy)

Tous les sélecteurs ci-dessous ont été validés dans `scrapy shell` **avant**
d'écrire les spiders, comme demandé par l'énoncé. Relevés le 29/07/2026.

Commande type utilisée :

```bash
scrapy shell "https://www.allocine.fr/film/meilleurs/" -s USER_AGENT="IPSSI-scraper (+contact@ipssi.fr)"
```

## AlloCiné

### Ce que dit l'énoncé et ce que répond le site

| Champ | Sélecteur de l'énoncé | Résultat en shell | Sélecteur retenu |
|---|---|---|---|
| carte liste | `h2.meta-title a` | 10 par page ✅ | inchangé |
| page suivante | `a.button--right::attr(href)` | **`None`** | voir ci-dessous |
| titre | `h1::text` | **chaîne vide** | `.titlebar-title::text` |
| année | `.meta-body-item strong::text` | `''` | 1ʳᵉ ligne de `.meta-body-info` |
| réalisateur | `.meta-body-direction a::text` | **`[]`** | `.meta-body-direction ::text`, 2ᵉ élément |
| note presse | `.stareval-note::text` | 1ʳᵉ note, sans garantie | par libellé, voir ci-dessous |
| note spectateurs | `.stareval-note:last-child::text` | **faux**, voir ci-dessous | par libellé |

### Le piège des notes

`.rating-item` renvoie les blocs de notation, mais **leur nombre et leur ordre
varient d'un film à l'autre**. Sur *Le Seigneur des anneaux : le retour du roi
(version longue)* :

```
RITEM 0 ['Spectateurs', '4,6', '3667 notes, 25 critiques']
RITEM 1 ['Mes amis', '--']
```

Il n'y a pas de note presse sur ce film, et le dernier bloc est « Mes amis »,
dont la valeur est `--`. Le sélecteur `.stareval-note:last-child` de l'énoncé
aurait donc rempli `note_spectateurs` avec `--` — c'est-à-dire `None` après cast,
alors que la note spectateurs existe bel et bien (4,6).

Le spider lit donc **le libellé du bloc** et range la valeur en conséquence :

```python
notes = {}
for bloc in response.css(".rating-item"):
    textes = [t.strip() for t in bloc.css("::text").getall() if t.strip()]
    if len(textes) >= 2:
        notes[textes[0]] = textes[1]
...
note_presse=notes.get("Presse"), note_spectateurs=notes.get("Spectateurs")
```

Résultat : sur 198 films, 0 note spectateurs manquante et 25 notes presse
absentes — des films sans critique presse, ce qui est la réalité du site.

### Le titre

`h1::text` renvoie une chaîne vide car le `<h1>` contient des nœuds enfants.
`"".join(response.css("h1 ::text").getall())` donne
`'Le Seigneur des anneaux : le retour du roi (version longue) de Peter Jackson'`
— titre **et** réalisateur collés. `.titlebar-title::text` isole proprement
`'Le Seigneur des anneaux : le retour du roi (version longue)'`.

### La pagination

`a.button--right` ne renvoie rien. Le bloc `.pagination` existe, mais :

```
['/film/meilleurs/?page=2', ..., '/film/meilleurs/?page=10',
 '/film/meilleurs/?page=20', '/film/meilleurs/?page=30']
```

soit 11 liens qui sautent de 10 à 20 puis 30 — et **sur la page 2, `.pagination`
est vide**. Impossible donc d'enchaîner de proche en proche. Le motif `?page=N`
étant vérifié en shell, le spider programme depuis la page 1 toutes les pages
jusqu'à `max_pages` :

```python
if page == 1:
    for n in range(2, self.max_pages + 1):
        yield response.follow(f"/film/meilleurs/?page={n}", callback=self.parse,
                              cb_kwargs={"page": n})
```

### L'User-Agent est obligatoire

Mesure en shell, même URL, seul l'UA change :

| User-Agent | Statut | Taille |
|---|---|---|
| défaut Scrapy (`Scrapy/2.17.0 (+https://scrapy.org)`) | **403** | 5 536 o |
| `IPSSI-scraper (+contact@ipssi.fr)` | 200 | 381 172 o |
| UA Chrome complet | 200 | 381 172 o |

L'UA honnête recommandé par le cours suffit : AlloCiné ne bloque que l'UA Scrapy
brut. Sans `USER_AGENT` dans `settings.py`, le TP entier échoue en 403.

## Boursorama

```
lignes    : table.c-table tbody tr        (filtrer sur >= 8 cellules)
cellules  : td.c-table__cell
identifiant : attribut data-ist du <tr>
pagination  : .c-pagination a::attr(href) -> /page-N?query
```

### L'ordre des colonnes de l'énoncé est faux

En-têtes réellement servis :

```
0 Libellé | 1 Dernier | 2 Var. | 3 Ouv | 4 +Haut | 5 +Bas | 6 Vol. | 7 Cap. bour.
```

L'énoncé lit `cells[3]` pour le volume. `cells[3]` est le **cours d'ouverture**.
Le code aurait tourné sans lever d'exception et rempli la colonne `volume` avec
un prix — l'erreur la plus dangereuse du TP, parce qu'elle est silencieuse et
que les données restent plausibles. Le volume est en `cells[6]`.

### Le second tableau

La page contient **deux** `table.c-table` : le palmarès (25 lignes, 8 colonnes)
et un widget latéral (5 lignes, 3 colonnes). `tr[data-ist]` en compte 30. Le
filtre `if len(cellules) < 8: continue` écarte le widget.

### Il n'y a pas d'ISIN

L'énoncé annonce « le code ISIN est souvent dans l'URL du lien ». C'est faux :
`/cours/1rPATE/` contient `1rPATE`, l'identifiant **interne Boursorama**, pas un
ISIN ISO 6166. Recherche exhaustive menée en shell :

- regex ISIN (`[A-Z]{2}[A-Z0-9]{9}[0-9]`) sur la page de listing : 0 occurrence
- même regex sur la fiche `/cours/1rPATE/` : 0 occurrence
- `"FR00"` dans le HTML : 0 occurrence
- `"isin"` en insensible à la casse : 7 occurrences… toutes à l'intérieur du mot
  `advertising` dans le CSS

Le vrai ISIN d'ALTEN est `FR0000071946` (visible dans la presse financière), mais
il n'est nulle part dans le HTML de Boursorama. La colonne `isin` de la table
est donc remplie avec `data-ist`, qui est stable et unique par valeur : la
contrainte `UNIQUE(isin)` demandée fonctionne, mais son contenu n'est pas un
ISIN. C'est écrit dans le code et dans le README.

## La Dépêche du Midi (défi 1)

```
carte  : article                          (37 sur la page Toulouse)
lien   : h2 a::attr(href)
titre  : h2 a ::text                      (avec l'espace : descend dans les enfants)
date   : absente du HTML -> extraite de l'URL /2026/07/29/...
```

`h2 a::text` (sans espace) renvoie une chaîne vide : le texte est dans des nœuds
enfants du lien. `h2 a ::text` avec l'espace descendant règle le problème, au
prix d'un `re.sub(r"\s+", " ", ...)` dans le pipeline pour recoller les morceaux.

Aucune balise `<time>` sur la page, et aucun attribut de date sur les cartes. La
date vient donc du chemin de l'URL, où elle est toujours présente sous la forme
`/AAAA/MM/JJ/`. C'est un sélecteur « structurel » plutôt que CSS — plus solide
qu'une classe, tant que le site ne change pas son schéma d'URL.
