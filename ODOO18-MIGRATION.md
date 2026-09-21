# Migration Odoo 12 → 18 : état et points bloquants

Relevé fait le 2026-09-21 contre `superquinquin.staging.foodcoop18.trobz.com`
(Odoo **18.0**, base `superquinquin_staging`), avec foodcoop12 (Odoo **12.0**)
comme référence de comparaison.

## Résumé

La migration applicative **ErpPeek → Odooly est terminée et validée** contre
Odoo 18 : `core gaps: 0`, 8 méthodes sur 10 passent. Les deux échecs restants
viennent du **serveur**, pas de la bibliothèque.

| # | Point | Nature | Bloque |
|---|-------|--------|--------|
| 1 | `/web/session/authenticate` plante | Régression de portage | Toute authentification RPC |
| 2 | `search()` cassé sur les modèles produit | Régression de portage | Recherche produit = cœur de la consigne |
| 3 | `sale_product_returnable` absent | Périmètre oublié | `returnable` / `return_product_id` |

Les points 2 et 3 sont **mis de côté** pour l'instant (décision du 2026-09-21).

---

## Point 1 — `/web/session/authenticate` plante

### Symptôme

Toute authentification RPC échoue avec `Invalid username or password`, alors
que **les mêmes identifiants fonctionnent sur l'interface web**.

### Cause

L'authentification réussit côté serveur ; c'est la construction de
`session_info` juste après qui lève :

```
addons/oca-server-ux/base_import_security_group/models/ir_http.py:15
    allowed_group_id = request.env.ref(allowed_group, raise_if_not_found=False)
AttributeError: 'NoneType' object has no attribute 'ref'
```

Le module OCA `base_import_security_group` surcharge `session_info()` et
suppose `request.env` disponible. Sur le chemin `authenticate`, il vaut `None`.
Le login web emprunte un autre chemin, d'où son fonctionnement.

### Pourquoi le message est trompeur

Odooly avale l'erreur (`odooly.py`, `_authenticate_session`) :

```python
except ServerError as exc:
    # Ignore: odoo.exceptions.AccessDenied
    if exc.args[0]['code'] not in (0, 200):
        raise
```

Le plantage sort en code 200, donc il est pris pour un `AccessDenied` et
rapporté en « identifiants invalides ». **Le message ne dit rien des
identifiants.** Même masquage pour `except TypeError: pass` (échec
d'extraction du `csrf_token` par regex).

### Contournement retenu

Pointer `ERP_URL` sur l'endpoint historique **`/jsonrpc`**, qui ne construit
pas `session_info` :

```
ERP_URL="https://superquinquin.staging.foodcoop18.trobz.com/jsonrpc"
```

Aucun changement de code : `OdooConnector.url` préserve le chemin.

### Conséquences

- **Portée** : affecte *tout* client RPC passant par l'endpoint web, pas
  seulement le nôtre. D'autres intégrations peuvent être cassées sans qu'on
  l'ait relié à cette cause.
- **Diagnostic détourné** : le défaut se déguise en problème d'identifiants.
  Coût constaté ici : plusieurs heures, une demande de déban inutile, et une
  rétractation erronée de ma part sur un constat pourtant juste.
- **Risque de bannissement IP** : `make_session()` retente 5 fois. Chaque
  reprise ressemble à une authentification ratée côté serveur ; un client
  avec reprises génère donc une rafale d'échecs apparents, de quoi déclencher
  la détection d'intrusion et faire bannir l'IP.
- **Fonctionnalité morte sans le contournement** : `auth_provider()`
  authentifie chaque opérateur au comptoir. Sans `/jsonrpc`, **aucun
  opérateur ne peut se connecter**.
- **Durée de vie limitée** : la documentation d'Odooly annonce `Client.common`
  et `Client._object` — les services derrière `/jsonrpc` — comme *Removed in
  Odoo 22*. Le contournement n'est donc pas pérenne au-delà d'Odoo 18.

### Correctif côté serveur

Rendre `base_import_security_group` tolérant à `request.env is None`, ou le
désinstaller s'il n'est pas utilisé.

---

## Point 2 — `search()` cassé sur les modèles produit *(mis de côté)*

### Symptôme

```
TypeError: ProductProduct.search() missing 1 required positional argument: 'domain'
```

| Modèle | `search()` | `search_count` / `search_read` / `name_search` |
|---|---|---|
| `res.partner`, `product.category`, `shift.shift`, `pos.order.line` | OK | OK |
| **`product.product`**, **`product.template`** | **CASSÉ** | OK |

### Cause

Une surcharge de `search()` **sans le décorateur `@api.model`**.

`call_kw` aiguille selon le décorateur : avec `@api.model` la méthode reçoit
`method(recs, *args)` ; sans lui, elle est traitée comme une méthode
d'enregistrements et `args[0]` est consommé comme liste d'ids. Le domaine est
donc mangé en guise d'ids.

Deux symptômes concordants :
- `args=[[]]` → le domaine est pris pour des ids, il ne reste rien →
  *missing 1 required positional argument*
- `args=[]` → pas même d'ids → *tuple index out of range*

**`search_read` fonctionne**, et il appelle `self.search()` en interne : la
surcharge est donc saine, seul l'aiguillage RPC est fautif.

### Candidats

Modules étendant `product.product` **et** `product.template` mais **pas**
`res.partner` (qui fonctionne) :

`barcodes_generator_product`, `coop_default_pricetag`,
`coop_product_coefficient`, `coop_stock`, `event_product`, `pos_meal_voucher`,
`product_analytic`, `product_average_consumption`, `product_history`,
**`product_multi_barcode`**, `product_print_category`,
`product_to_scale_bizerba`, `stock_account`, `website_sale_stock`

Favori : `product_multi_barcode`, dont la raison d'être est de faire trouver
un produit par l'un quelconque de ses codes-barres — ce qui se fait en
surchargeant `search()`. Hypothèse rangée par vraisemblance, non vérifiée :
les modules standards de la liste casseraient partout ailleurs.

### Correctif

Ajouter `@api.model` au-dessus de la surcharge. Localisation :

```bash
grep -rn -B3 "def search(" addons/*/models/product*.py | grep -v "api.model"
```

### Contournement possible (non implémenté)

Router les recherches par domaine via `search_read` puis `browse()`, qui
fonctionne sur 12 comme sur 18. Écarté pour l'instant : c'est un
contournement d'un bug serveur, et il ajoute de l'indirection dans le joint
de session. À faire inconditionnellement plutôt qu'en repli sur `TypeError` —
un repli sur exception masquerait la prochaine régression du même genre.

---

## Point 3 — `sale_product_returnable` absent *(mis de côté)*

### Constat

`returnable` et `return_product_id` sont absents de `product.template` sur
Odoo 18. Ce ne sont pas des renommages : **aucun** champ contenant
`return`, `consign` ou `deposit` n'existe sur `product.template` ni sur
`product.product`.

En revanche les catégories `Consigne` (181), `Consigne_product` (182) et
`Consigne_return` (183) **ont bien été migrées** : les données sont là, le
module qui définit les champs ne l'est pas.

### Module responsable

Identifié via `ir.model.data` sur foodcoop12 :

| Champ | Module | Type |
|---|---|---|
| `returnable` | `sale_product_returnable` | boolean |
| `return_product_id` | `sale_product_returnable` | many2one → `product.product` |
| `barcode_base` | `barcodes_generator_product` | integer *(présent en 18)* |
| `fiscal_classification_id` | `account_product_fiscal_classification` | many2one *(présent en 18)* |

### Statut amont

`sale_product_returnable` n'existe que sur la branche **12.0** de
`OCA/sale-workflow`. Absent des branches 16.0, 17.0 et 18.0, et introuvable
dans `OCA/product-attribute` et `OCA/stock-logistics-workflow`.

**OCA ne l'a jamais porté au-delà d'Odoo 12.** Il s'agit donc d'un portage à
faire, pas d'une installation. Le module est petit : un booléen et un
many2one sur `product.template`, plus les vues.

---

## Ce qui est bien porté en Odoo 18

Vérifié présent : `shift.shift`, `shift.registration` (tous champs),
`res.partner.barcode_base`, `res.partner.cooperative_state`,
`product.template.barcode_base`, `product.template.fiscal_classification_id`,
`pos.order.line` (tous champs), et la suite `coop_*` complète
(`coop_shift`, `coop_membership`, `coop_point_of_sale`, …).

L'inquiétude initiale sur l'absence de port public des addons foodcoop
(`AwesomeFoodCoops/odoo-production` s'arrête en 12.0, `beescoop/Obeesdoo` en
16.0) **était infondée** : le portage a été fait côté hébergeur.

---

## Relancer la validation

```bash
cd api
set -a && . ./.env && set +a
ERP_URL="https://superquinquin.staging.foodcoop18.trobz.com/jsonrpc" \
  python -m src.scripts.validate_odoo
```

Le script tente **une seule** authentification, sans reprise, puis inventorie
les modèles et champs requis (en distinguant cœur Odoo et addons) et propose
les renommages probables pour chaque champ absent.

Les environnements Trobz sont protégés par une détection d'intrusion :
supposer chaque passage unique, ne jamais rejouer une authentification en
échec, et ne jamais provoquer de 401 délibéré.
