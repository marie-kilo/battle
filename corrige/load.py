"""Accès base : schéma, comptages de reprise, insertions."""

import io
import os
import pathlib

import psycopg2
from psycopg2.extras import execute_values

SCHEMA = pathlib.Path(__file__).resolve().parent / "schema.sql"


def connect():
    return psycopg2.connect(os.environ.get("DATABASE_URL", "dbname=megabase0"))


def create_schema(cur):
    cur.execute(SCHEMA.read_text())


def count_rows(cur, table, dept):
    """Lignes du département déjà présentes (préfixe du code INSEE).

    - 💡 les lignes rattachées à la commune sentinelle 99999 ne sont pas
    comptées : le comptage sous-estime (mais jamais l'inverse). Une reprise
    utilisant ce comptage relit des lignes déjà insérées, elle n'en
    saute aucune.
    """
    cur.execute(f"SELECT count(*) FROM {table} WHERE insee_code LIKE %s", (dept + "%",))
    return cur.fetchone()[0]


def count_stream(cur, table, dept):
    """Lignes déjà insérées par le flux de collecte du département.

    Le comptage se fait sur dep_code, pas sur le code INSEE : les lignes en
    commune sentinelle et les communes de départements voisins (réseaux
    d'eau à cheval) comptent pour le flux qui les a produites. Un comptage
    par préfixe INSEE surestimerait la pagination du département voisin et
    lui ferait sauter des pages.
    """
    cur.execute(f"SELECT count(*) FROM {table} WHERE dep_code = %s", (dept,))
    return cur.fetchone()[0]


def communes_restantes(cur, table, dept):
    """Codes INSEE du département absents de la table cible.

    Reprise à la commune : seules les communes jamais chargées sont
    redemandées à l'API. Une commune sans donnée dans la source est
    redemandée à chaque run (limite documentée dans le README).
    """
    cur.execute(
        f"""
        SELECT insee_code FROM commune
        WHERE code_departement = %s
          AND insee_code NOT IN (SELECT DISTINCT insee_code FROM {table})
        ORDER BY insee_code
        """,
        (dept,),
    )
    return [ligne[0] for ligne in cur.fetchall()]


def insert_geography(cur, raw_communes):
    """Insère région, département, commune (dans l'ordre des clés étrangères).

    geo.api donne pour chaque commune son département et sa région (code +
    nom). Renvoie l'ensemble des codes INSEE connus.
    """
    regions, departements, communes = {}, {}, []
    for c in raw_communes:
        dep = c.get("departement") or {}
        reg = c.get("region") or {}
        if reg.get("code"):
            regions[reg["code"]] = (reg["code"], reg["nom"])
        if dep.get("code"):
            departements[dep["code"]] = (dep["code"], dep["nom"], reg.get("code"))
        communes.append((c["code"], c["nom"], c.get("population"), dep.get("code")))

    cur.executemany(
        "INSERT INTO region (code_region, name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        list(regions.values()),
    )
    cur.executemany(
        "INSERT INTO departement (code_departement, name, code_region) "
        "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        list(departements.values()),
    )
    cur.executemany(
        "INSERT INTO commune (insee_code, name, population, code_departement) "
        "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
        communes,
    )
    return {c[0] for c in communes}


def insert_chunk(cur, table, chunk):
    """Insère une liste de dicts. Les colonnes sont les clés des dicts.

    La clé reseaux, portée par les dicts de qualite_eau_potable, n'est pas
    une colonne : elle est écartée ici et consommée par insert_reseaux.
    """
    if not chunk:
        return
    columns = [k for k in chunk[0] if k != "reseaux"]
    placeholders = ", ".join(f"%({c})s" for c in columns)
    cur.executemany(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT DO NOTHING",
        chunk,
    )


def insert_reseaux(cur, chunk):
    """Insère les réseaux portés par un chunk de prélèvements, puis les
    liaisons prélèvement-réseau."""
    reseaux_rows = []
    liens_rows = []
    for r in chunk:
        if not r["identifiant"]:
            continue
        for res in r.get("reseaux", []):
            reseaux_rows.append((res["code_reseau"], res["nom_reseau"]))
            liens_rows.append((r["identifiant"], res["code_reseau"]))
    if reseaux_rows:
        execute_values(
            cur,
            "INSERT INTO reseau (code_reseau, nom_reseau) VALUES %s ON CONFLICT DO NOTHING",
            reseaux_rows,
        )
    if liens_rows:
        # la jointure de garde ne lie que des prélèvements présents dans
        # qualite_eau_potable : aucune violation de clé étrangère possible
        execute_values(
            cur,
            """
            INSERT INTO qualite_eau_potable_reseau (identifiant, code_reseau)
            SELECT v.identifiant, v.code_reseau
            FROM (VALUES %s) AS v(identifiant, code_reseau)
            JOIN qualite_eau_potable q ON q.identifiant = v.identifiant
            ON CONFLICT DO NOTHING
            """,
            liens_rows,
        )


def insert_udi(cur, chunk):
    """Insère les réseaux puis les rattachements commune-réseau.

    L'ordre respecte la clé étrangère de commune_reseau vers reseau.
    """
    if not chunk:
        return
    reseaux = {(r["code_reseau"], r["nom_reseau"]) for r in chunk if r["code_reseau"]}
    execute_values(
        cur,
        "INSERT INTO reseau (code_reseau, nom_reseau) VALUES %s ON CONFLICT DO NOTHING",
        list(reseaux),
    )
    liens = [
        (r["insee_code"], r["code_reseau"], r["annee"], r["debut_alim"])
        for r in chunk
        if r["code_reseau"]
    ]
    execute_values(
        cur,
        "INSERT INTO commune_reseau (insee_code, code_reseau, annee, debut_alim) "
        "VALUES %s ON CONFLICT DO NOTHING",
        liens,
    )


def reattache_sentinelles(cur):
    """Réaffecte les lignes en sentinelle dont la commune est connue.

    Une ligne est affectée à la commune sentinelle quand son code commune
    est absent du référentiel (département voisin pas encore chargé). Le
    code brut conservé dans code_commune_source permet la réaffectation
    dès que la commune entre dans le référentiel. Renvoie le nombre de
    lignes réaffectées.
    """
    cur.execute(
        """
        UPDATE qualite_eau_potable q
        SET insee_code = q.code_commune_source
        FROM commune c
        WHERE q.insee_code = '99999'
          AND c.insee_code = q.code_commune_source
        """
    )
    return cur.rowcount


def copy_mutations(cur, df):
    """Insertion en masse d'un DataFrame dans mutation, par COPY (format csv).

    Une seule commande pour tout le département. Les cellules vides du CSV
    deviennent des NULL.
    """
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False)
    buf.seek(0)
    cur.copy_expert(
        f"COPY mutation ({', '.join(df.columns)}) FROM STDIN WITH (FORMAT csv)",
        buf,
    )
