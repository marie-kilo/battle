"""Hub'Eau resultats_dis : les analyses de qualité de l'eau potable.


LLM comment :

L'endpoint accepte code_departement et pagine au-delà de 20 000 lignes
(réponse 206 avec lien next, mesure du 12 juillet 2026). L'historique complet du
département 90, le moins peuplé, compte 244 014 lignes : la collecte est
bornée par une fenêtre date_min_prelevement de 12 mois, soit 14 412 lignes
pour ce même département à la même date. Chaque ligne est la mesure d'un
paramètre sur un prélèvement ; le couple (code_prelevement, code_parametre)
est unique dans la source et sert de clé primaire.

Le filtre code_departement porte sur le flux de distribution, pas sur la
commune : un réseau à cheval sur deux départements produit des lignes de
communes voisines (5 014 lignes de communes des départements 69, 71, 38 et
39 dans le flux du département 01, mesure du 12 juillet 2026). Ces lignes
sont affectées à la commune sentinelle tant que la commune est inconnue,
le code brut est conservé dans code_commune_source, et
load.reattache_sentinelles les réaffecte dès que le département voisin
est chargé.

Reprise à la page : le nombre de lignes déjà insérées par ce flux
(comptage sur dep_code) divisé par la taille de page donne une page de
départ inférieure ou égale à la page réelle. Les lignes relues sont
ignorées par ON CONFLICT DO NOTHING.

Usage : python3 qualite_eau.py 69
"""

import os
import sys

import requests

import clean
import collect
import load

URL = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable/resultats_dis"
PER_PAGE = 20000  # taille maximale acceptée par l'API

# Borne basse de la fenêtre de collecte, portée par la variable
# d'environnement DATE_MIN. Une valeur vide supprime la borne : la source
# est alors chargée sur tout son historique. La reprise à la page suppose
# une valeur constante entre les runs d'un même département ; un
# changement de fenêtre impose de vider la table de ce flux.
DATE_MIN = os.environ.get("DATE_MIN", "2025-07-01")

# Sélection de champs : une ligne complète de l'API porte 32 champs, la
# table en conserve 10.
FIELDS = ",".join(
    [
        "code_commune",
        "code_prelevement",
        "code_parametre",
        "libelle_parametre",
        "resultat_alphanumerique",
        "resultat_numerique",
        "libelle_unite",
        "date_prelevement",
        "conclusion_conformite_prelevement",
        "reseaux",
    ]
)

DEPT = (sys.argv[1] if len(sys.argv) > 1 else "69").upper().zfill(2)


def main():
    conn = load.connect()
    cur = conn.cursor()
    load.create_schema(cur)

    print(f"=== qualite_eau département {DEPT} ===", flush=True)

    try:
        raw_communes = collect.fetch_communes(DEPT)
    except requests.RequestException as e:
        print(
            f"  géographie indisponible ({type(e).__name__}), relance qualite_eau.py {DEPT}",
            flush=True,
        )
        conn.close()
        sys.exit(1)
    known_communes = load.insert_geography(cur, raw_communes)
    conn.commit()

    already = load.count_stream(cur, "qualite_eau_potable", DEPT)
    page = already // PER_PAGE + 1

    while True:
        params = {
            "code_departement": DEPT,
            "fields": FIELDS,
            "size": PER_PAGE,
            "page": page,
        }
        if DATE_MIN:
            params["date_min_prelevement"] = DATE_MIN
        donnees = collect.fetch_json(URL, params, timeout=300)
        if donnees is None:
            print(f"  API indisponible, relance qualite_eau.py {DEPT} pour reprendre", flush=True)
            conn.close()
            sys.exit(1)

        results = donnees.get("data", [])
        if not results:
            break

        chunk = []
        for row in results:
            r = clean.clean_qualite(row)
            if not r["identifiant"]:
                continue
            r["dep_code"] = DEPT
            if r["insee_code"] not in known_communes:
                r["insee_code"] = "99999"
            chunk.append(r)
        load.insert_chunk(cur, "qualite_eau_potable", chunk)
        load.insert_reseaux(cur, chunk)
        conn.commit()  # commit par page : un run interrompu conserve les pages validées

        if not donnees.get("next"):
            break
        page += 1

    rattachees = load.reattache_sentinelles(cur)
    conn.commit()
    if rattachees:
        print(f"  {rattachees} lignes réaffectées depuis la sentinelle", flush=True)

    print(f"qualite_eau_potable: {load.count_stream(cur, 'qualite_eau_potable', DEPT)}", flush=True)
    conn.close()


if __name__ == "__main__":
    main()
