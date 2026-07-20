# Attribution 

- le squelette `corrige0` fourni en formation
- le rendu du groupe anonymous 
- le rendu du groupe lazarus


## 1. Vue par fichier

| Fichier du corrigé | Origine principale | Contenu repris | Modifications |
|---|---|---|---|
| `collect.py` | squelette `corrige0` | `fetch_communes`, session à User-Agent explicite | `fetch_json` (tentatives espacées de 60 s) ajouté |
| `clean.py` | lazarus | `clean_eau` (renommé `clean_qualite`), `normalize_insee`, `DISTRICTS`, `_to_float` | colonnes `dep_code` et `code_commune_source` ajoutées ; `clean_udi` et `clean_risques` ajoutés |
| `load.py` | squelette et lazarus | `insert_geography`, `insert_chunk`, `insert_reseaux` | `count_stream`, `communes_restantes`, `insert_udi`, `reattache_sentinelles`, `copy_mutations` ajoutés |
| `schema.sql` | les deux groupes | géographie du squelette ; `qualite_eau_potable`, `reseau` et liaison (lazarus) ; clé (num_risque, insee_code) et sentinelle 99999 (anonymous) | index sur les clefs étrangères, colonnes `dep_code` et `code_commune_source` ajoutés |
| `geo_risque.py` | anonymous | lots de 10 codes INSEE, aplatissement de `risques_detail` | reprise à la commune, arrêt propre, pause de 0,5 s |
| `reseau_eau.py` | anonymous | interface `communes_udi` | appels par lots de 10 au lieu d'un appel par commune ; modèle normalisé (lazarus) |
| `qualite_eau.py` | lazarus | pagination de `resultats_dis` par `code_departement`, reprise par comptage, clé naturelle | fenêtre `DATE_MIN`, sélection de champs, comptage sur `dep_code`, sentinelle et réaffectation |
| `dvf.py` | anonymous | fichiers annuels csv.gz, nettoyage pandas, sentinelle 99999 | reprise au département sans `sys.exit`, transaction unique, insertion par COPY, colonnes utiles conservées |
| `run_all.py` | lazarus | boucle subprocess par département, suivi des échecs | code de sortie, sélection de départements en argument |
| `Procfile` | anonymous | worker Scalingo | commande unique `run_all.py` |

## 2. Vue par source

### 2.1 Géorisques (GASPAR)

Le script de anonymous (`geo_risque.py`) fonctionne : 
- lots de 10 communes
- "flattening" de la réponse imbriquée
- clé primaire composée

🟠 Ses défauts sont : 
- `break` qui interrompt le département entier sur un lot vide ou une erreur d'API
- des variables mortes (`page`, `seen`, `nb_rows`) 
- l'absence de nettoyage des clés JSON


🟠 Le script de lazarus (`georisque_gaspar.py`) ne peut pas s'exécuter :

- l'URL est celle de Hub'Eau (`resultats_dis`) (et pas de Géorisques)
- la ligne 60 lit une clef `id` alors que le nettoyage produit `id_georisque` (le nom de colonne diverge du schéma)
- La source n'est pas intégrée dans ce rendu

> 🟢 Le corrigé reprend la méthode de anonymous et la reprise à la commune.

### 2.2 Eau, réseaux de distribution (communes_udi)

Le script de anonymous (`reseau_eaux.py`) est le seul à exploiter cette interface : 
- il émet un appel par commune (34 875 appels pour la France) 
- il recharge la géographie du département à chaque commune 
- la table cible n'a pas de contrainte d'unicité (`to_sql(if_exists="append")`)

lazarus n'utilise pas cet endpoint : 
- son référentiel des réseaux provient des listes `reseaux`  (`resultats_dis`) 
- avec une table `reseau` normalisée 
- et une table de liaison many-to-many alimentée par un INSERT...SELECT

> 🟢 Le corrigé croise les deux : l'interface de anonymous, par lots de 10 + le modèle normalisé de lazarus.

### 2.3 Eau, analyses de qualité (resultats_dis)

Le script de lazarus (`eau.py`) est la meilleure des deux versions :

- clé naturelle avec `(code_prelevement, code_parametre)`
- dédoublonnage
- liaisons prélèvement-réseau.

La version de anonymous (`eau.py`) charge la même interface dans une table (clef SERIAL) sans contrainte d'unicité, ce qui
autorise les doublons à la relance.

> 🟢 Le corrigé reprend la version de lazarus et la borne par la fenêtre `DATE_MIN`.

### 2.4 DVF (mutations foncières)

Le script de anonymous (`dvf.py`) : 
- conserve les colonnes utiles (valeur foncière, date, nature, type de local)
- lit les fichiers annuels csv.gz 
- 💜 introduit la commune "sentinelle" 99999
- Ses défauts sont un `sys.exit(0)` au premier département déjà chargé qui neutralise toute
relance en boucle
- un test de reprise `count > 0` qui tient un département partiel pour complet

Le script de lazarus (`dvf.py`) : 
- ne conserve ni valeur foncière, ni date, ni type de bien 
- sa fonction `get_batch` renvoie `None` sur le dernier lot partiel (donc il y a deslignes perdues) 
- l'offset de reprise s'applique deux fois

> 🟢 Le corrigé reprend le choix des fichiers, le nettoyage pandas et la sentinelle de anonymous ; l'atomicité par transaction unique et
l'insertion par COPY sont des ajouts.

## 3. Éléments ajoutés

- La colonne `dep_code` et le comptage par flux (`count_stream`)
- la colonne `code_commune_source` et la réaffectation des sentinelles
(`reattache_sentinelles`)
- la fenêtre `DATE_MIN`, la sélection de champs de `resultats_dis`
- l'insertion par `COPY ... FROM STDIN`
- les index sur les clés étrangères
-les nouvelles tentatives centralisées dans `fetch_json` 
- le code de sortie de `run_all.py` 

## 4. Limites de l'attribution

- historique lazarus = 2 commits (un seul auteur, donc pas d'attribution intra-groupe)
- historique anonymous = 42 commits (3 auteurs)
