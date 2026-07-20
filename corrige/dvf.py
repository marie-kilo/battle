"""DVF : les mutations foncières, fichiers annuels de data.gouv.fr.

La source est le dépôt geo-dvf (files.data.gouv.fr/geo-dvf), un fichier
csv.gz par département et par millésime, pas une API : le fichier 2025 du
département 90 pèse 166 Ko pour 7 097 lignes. Le fichier ne fournit aucune
clé par ligne (une mutation couvre plusieurs parcelles et locaux).
Conséquences :
- reprise au département : un département présent dans mutation est
  considéré chargé et sauté ;
- insertion du département entier dans une transaction unique : un run
  interrompu ne laisse aucune ligne, la relance repart de zéro pour ce
  département

Les codes INSEE absents du référentiel sont rattachés à la commune
sentinelle 99999 (schema.sql) au lieu d'être rejetés.

- La source ne couvre ni la Moselle (57), ni le Bas-Rhin (67), ni le Haut-Rhin (68), la publicité foncière y relevant du Livre foncier d'Alsace-Moselle, ni Mayotte (976).
- Les quatre fichiers répondent 404 (constaté le 13 juillet 2026) ; l'absence est consignée et le collecteur se termine sans erreur.

Usage : python3 dvf.py 69
"""

import io
import sys

import pandas as pd
import requests

import clean
import collect
import load

MILLESIME = "2025"
URL = f"https://files.data.gouv.fr/geo-dvf/latest/csv/{MILLESIME}/departements"

# Le fichier source compte 40 colonnes ; 10 sont conservées. usecols
# limite la lecture à ces colonnes.
COLONNES = [
    "id_mutation",
    "date_mutation",
    "nature_mutation",
    "valeur_fonciere",
    "id_parcelle",
    "type_local",
    "nombre_pieces_principales",
    "longitude",
    "latitude",
    "code_commune",
]

DEPT = (sys.argv[1] if len(sys.argv) > 1 else "69").upper().zfill(2)


def main():
    conn = load.connect()
    cur = conn.cursor()
    load.create_schema(cur)

    print(f"=== dvf département {DEPT} ===", flush=True)

    try:
        raw_communes = collect.fetch_communes(DEPT)
    except requests.RequestException as e:
        print(f"  géographie indisponible ({type(e).__name__}), relance dvf.py {DEPT}", flush=True)
        conn.close()
        sys.exit(1)
    known_communes = load.insert_geography(cur, raw_communes)
    conn.commit()

    deja = load.count_stream(cur, "mutation", DEPT)
    if deja:
        print(f"mutation: {deja} (déjà chargé)", flush=True)
        conn.close()
        return

    try:
        contenu = collect.fetch_fichier(f"{URL}/{DEPT}.csv.gz")
    except requests.RequestException as e:
        print(f"  source indisponible ({type(e).__name__}), relance dvf.py {DEPT}", flush=True)
        conn.close()
        sys.exit(1)
    if contenu is None:
        print(f"mutation: source absente pour {DEPT} (404)", flush=True)
        conn.close()
        return

    df = pd.read_csv(io.BytesIO(contenu), compression="gzip", dtype=str, usecols=COLONNES)
    df = df[COLONNES]

    df["insee_code"] = df["code_commune"].map(clean.normalize_insee)
    df.loc[~df["insee_code"].isin(known_communes), "insee_code"] = "99999"
    df["dep_code"] = DEPT
    df = df.drop(columns=["code_commune"])

    df["valeur_fonciere"] = pd.to_numeric(df["valeur_fonciere"], errors="coerce")
    df["nombre_pieces_principales"] = pd.to_numeric(
        df["nombre_pieces_principales"], errors="coerce"
    ).astype("Int64")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")

    load.copy_mutations(cur, df)
    conn.commit()  # transaction unique : un run interrompu ne laisse aucune ligne

    print(f"mutation: {load.count_stream(cur, 'mutation', DEPT)}", flush=True)
    conn.close()


if __name__ == "__main__":
    main()
