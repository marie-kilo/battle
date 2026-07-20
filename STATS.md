# Extraction des bases Scalingo des 2 groupes

- extraction du 13 juillet 2026. Une table par sous-dossier
- chunks CSV de 10 000 lignes au plus 
- en-tête répété dans chaque fichier
- terminateur de ligne `\n`
- Lecture seule (`COPY ... TO STDOUT`)
- chaque table a été vérifiée : lignes exportées égales au `count(*)` de la base (colonne « écart »).
- les tables à 0 ligne sont conservées avec leur en-tête seul, pour tracer le schéma complet de chaque base.

## anonymous (les-anonymous)

- 17 tables
- 2 853 701 lignes
- 300 fichiers
- Tables non vides : 7

| Table | Lignes | Fichiers | Écart |
|---|---|---|---|
| `bibliotheque` | 0 | 1 | 0 |
| `clubs_boxe_thai` | 0 | 1 | 0 |
| `college` | 0 | 1 | 0 |
| `commune` | 33 724 | 4 | 0 |
| `dechets_radioactifs` | 0 | 1 | 0 |
| `departement` | 90 | 1 | 0 |
| `dvf` | 127 303 | 13 | 0 |
| `eau` | 2 512 824 | 252 | 0 |
| `ehpad` | 0 | 1 | 0 |
| `entreprise_btp` | 0 | 1 | 0 |
| `gare` | 0 | 1 | 0 |
| `geo_risque` | 172 780 | 18 | 0 |
| `lycee` | 0 | 1 | 0 |
| `mairie` | 0 | 1 | 0 |
| `pharmacie` | 0 | 1 | 0 |
| `region` | 14 | 1 | 0 |
| `reseau_eau` | 6 966 | 1 | 0 |

## lazarus (les-lazarus)

- 22 tables
- 95 396 344 lignes
- 9560 fichiers
- tables non vides : 7

| Table | Lignes | Fichiers | Écart |
|---|---|---|---|
| `bibliotheque` | 0 | 1 | 0 |
| `boulangerie` | 0 | 1 | 0 |
| `college` | 0 | 1 | 0 |
| `commune` | 34 875 | 4 | 0 |
| `departement` | 101 | 1 | 0 |
| `ehpad` | 0 | 1 | 0 |
| `entreprise_btp` | 0 | 1 | 0 |
| `equipement_sport` | 0 | 1 | 0 |
| `gare` | 0 | 1 | 0 |
| `georisque_gaspar` | 0 | 1 | 0 |
| `installation_sport` | 0 | 1 | 0 |
| `jardin` | 0 | 1 | 0 |
| `lycee` | 0 | 1 | 0 |
| `mairie` | 34 875 | 4 | 0 |
| `musee` | 0 | 1 | 0 |
| `mutation` | 0 | 1 | 0 |
| `pharmacie` | 0 | 1 | 0 |
| `qualite_eau_potable` | 39 100 273 | 3911 | 0 |
| `qualite_eau_potable_reseau` | 56 202 678 | 5621 | 0 |
| `region` | 18 | 1 | 0 |
| `reseau` | 23 524 | 3 | 0 |
| `theatre` | 0 | 1 | 0 |
