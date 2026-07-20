-- Géographie en 3 niveaux (région > département > commune), reliés par clés
-- étrangères. Tables conservées d'un run à l'autre : un chargement interrompu
-- peut reprendre.

CREATE TABLE IF NOT EXISTS region (
    code_region TEXT PRIMARY KEY,
    name        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS departement (
    code_departement TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    code_region      TEXT REFERENCES region (code_region)
);

CREATE TABLE IF NOT EXISTS commune (
    insee_code       TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    population       INTEGER,
    code_departement TEXT REFERENCES departement (code_departement)
);

-- Commune sentinelle : les codes INSEE absents du référentiel sont rattachés
-- à 99999 au lieu d'être rejetés. La contrainte de clé étrangère est
-- respectée sans perte de lignes.
INSERT INTO region VALUES ('99', 'Inconnue') ON CONFLICT DO NOTHING;
INSERT INTO departement VALUES ('99', 'Inconnu', '99') ON CONFLICT DO NOTHING;
INSERT INTO commune VALUES ('99999', 'Commune inconnue', 0, '99') ON CONFLICT DO NOTHING;

-- Risques GASPAR : une ligne par couple (commune, risque). La clé primaire
-- composée rend la relance idempotente.
CREATE TABLE IF NOT EXISTS geo_risque (
    insee_code          TEXT NOT NULL REFERENCES commune (insee_code),
    num_risque          TEXT NOT NULL,
    libelle_risque_long TEXT,
    PRIMARY KEY (insee_code, num_risque)
);

-- Référentiel des réseaux de distribution d'eau potable.
CREATE TABLE IF NOT EXISTS reseau (
    code_reseau TEXT PRIMARY KEY,
    nom_reseau  TEXT
);

-- Rattachement commune-réseau (many-to-many), une ligne par année de
-- référence. Une commune peut dépendre de plusieurs réseaux (quartiers).
CREATE TABLE IF NOT EXISTS commune_reseau (
    insee_code  TEXT NOT NULL REFERENCES commune (insee_code),
    code_reseau TEXT NOT NULL REFERENCES reseau (code_reseau),
    annee       TEXT NOT NULL,
    debut_alim  DATE,
    PRIMARY KEY (insee_code, code_reseau, annee)
);

-- Analyses de qualité de l'eau : une ligne par paramètre mesuré sur un
-- prélèvement. identifiant = code_prelevement + code_parametre, couple
-- unique dans la source. dep_code est le département du flux de collecte,
-- pas celui de la commune : un réseau de distribution chevauche les
-- départements, l'API renvoie donc des communes voisines. Le code commune
-- brut est conservé dans code_commune_source pour la réaffectation des
-- lignes en sentinelle (load.reattache_sentinelles).
CREATE TABLE IF NOT EXISTS qualite_eau_potable (
    identifiant             TEXT PRIMARY KEY,
    code_prelevement        TEXT,
    libelle_parametre       TEXT,
    resultat_alphanumerique TEXT,
    resultat_numerique      DOUBLE PRECISION,
    libelle_unite           TEXT,
    date_prelevement        TIMESTAMPTZ,
    conclusion_conformite   TEXT,
    dep_code                TEXT NOT NULL,
    code_commune_source     TEXT,
    insee_code              TEXT REFERENCES commune (insee_code)
);

-- Liaison prélèvement-réseau (many-to-many) : la source porte la liste des
-- réseaux sur chaque ligne d'analyse.
CREATE TABLE IF NOT EXISTS qualite_eau_potable_reseau (
    identifiant TEXT REFERENCES qualite_eau_potable (identifiant),
    code_reseau TEXT REFERENCES reseau (code_reseau),
    PRIMARY KEY (identifiant, code_reseau)
);

-- Mutations foncières DVF. Le fichier source ne fournit aucune clé par ligne
-- (une mutation couvre plusieurs parcelles et locaux) : clé technique, et
-- reprise au département par la colonne dep_code.
CREATE TABLE IF NOT EXISTS mutation (
    id                        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_mutation               TEXT,
    date_mutation             DATE,
    nature_mutation           TEXT,
    valeur_fonciere           DOUBLE PRECISION,
    id_parcelle               TEXT,
    type_local                TEXT,
    nombre_pieces_principales INTEGER,
    longitude                 DOUBLE PRECISION,
    latitude                  DOUBLE PRECISION,
    dep_code                  TEXT NOT NULL,
    insee_code                TEXT REFERENCES commune (insee_code)
);

-- PostgreSQL n'indexe pas les colonnes référençantes d'une clé étrangère :
-- index posés sur les colonnes de jointure des requêtes d'analyse.
CREATE INDEX IF NOT EXISTS idx_qualite_insee ON qualite_eau_potable (insee_code);
CREATE INDEX IF NOT EXISTS idx_qualite_dep ON qualite_eau_potable (dep_code);
CREATE INDEX IF NOT EXISTS idx_qualite_reseau_reseau ON qualite_eau_potable_reseau (code_reseau);
CREATE INDEX IF NOT EXISTS idx_commune_reseau_reseau ON commune_reseau (code_reseau);
CREATE INDEX IF NOT EXISTS idx_mutation_insee ON mutation (insee_code);
CREATE INDEX IF NOT EXISTS idx_mutation_dep ON mutation (dep_code);
