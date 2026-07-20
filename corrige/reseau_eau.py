"""Hub'Eau communes_udi : le rattachement des communes aux réseaux d'eau.



LLM comment :

L'endpoint ignore le paramètre code_departement (50 296 lignes renvoyées
quelle que soit sa valeur, mesure du 12 juillet 2026). Les codes commune sont
donc passés explicitement, par lots de 10, lus dans la table commune.
Reprise à la commune, comme geo_risque.py.

Usage : python3 reseau_eau.py 69
"""

import sys
import time

import requests

import clean
import collect
import load

URL = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable/communes_udi"
ANNEE = "2025"  # année de référence du rattachement
LOT = 10
PAUSE = 0.5  # secondes entre deux lots, pour rester sous le plafond de débit

DEPT = (sys.argv[1] if len(sys.argv) > 1 else "69").upper().zfill(2)


def main():
    conn = load.connect()
    cur = conn.cursor()
    load.create_schema(cur)

    print(f"=== reseau_eau département {DEPT} ===", flush=True)

    try:
        raw_communes = collect.fetch_communes(DEPT)
    except requests.RequestException as e:
        print(
            f"  géographie indisponible ({type(e).__name__}), relance reseau_eau.py {DEPT}",
            flush=True,
        )
        conn.close()
        sys.exit(1)
    load.insert_geography(cur, raw_communes)
    conn.commit()

    codes = load.communes_restantes(cur, "commune_reseau", DEPT)
    if not codes:
        print(
            f"commune_reseau: {load.count_rows(cur, 'commune_reseau', DEPT)} (déjà chargé)",
            flush=True,
        )
        conn.close()
        return

    for i in range(0, len(codes), LOT):
        donnees = collect.fetch_json(
            URL,
            {
                "code_commune": ",".join(codes[i : i + LOT]),
                "annee": ANNEE,
                "size": 1000,
            },
        )
        if donnees is None:
            print(f"  API indisponible, relance reseau_eau.py {DEPT} pour reprendre", flush=True)
            conn.close()
            sys.exit(1)
        chunk = [clean.clean_udi(row) for row in donnees.get("data", [])]
        load.insert_udi(cur, chunk)
        conn.commit()  # commit par lot : un run interrompu conserve les lots validés
        time.sleep(PAUSE)

    print(f"commune_reseau: {load.count_rows(cur, 'commune_reseau', DEPT)}", flush=True)
    conn.close()


if __name__ == "__main__":
    main()
