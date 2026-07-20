"""Géorisques GASPAR : les risques recensés par commune.

- l'endpoint /v1/gaspar/risques accepte au plus 10 codes INSEE par appel (paramètre code_insee)
- il renvoie une entrée par commune, portant la liste imbriquée risques_detail
- la collecte passe donc par lots de 10 communes lues dans la table commune
- 🟠 reprise à la commune : seules les communes absentes de geo_risque sont redemandées

Usage : python3 geo_risque.py 69
"""

import sys
import time

import requests

import clean
import collect
import load

URL = "https://georisques.gouv.fr/api/v1/gaspar/risques"
LOT = 10  # plafond de codes INSEE par appel
PAUSE = 0.5  # secondes entre deux lots, pour rester sous le plafond de débit

DEPT = (sys.argv[1] if len(sys.argv) > 1 else "69").upper().zfill(2)


def main():
    conn = load.connect()
    cur = conn.cursor()
    load.create_schema(cur)

    print(f"=== geo_risque département {DEPT} ===", flush=True)

    try:
        raw_communes = collect.fetch_communes(DEPT)
    except requests.RequestException as e:
        print(
            f"  géographie indisponible ({type(e).__name__}), relance geo_risque.py {DEPT}",
            flush=True,
        )
        conn.close()
        sys.exit(1)
    load.insert_geography(cur, raw_communes)
    conn.commit()

    codes = load.communes_restantes(cur, "geo_risque", DEPT)
    if not codes:
        print(f"geo_risque: {load.count_rows(cur, 'geo_risque', DEPT)} (déjà chargé)", flush=True)
        conn.close()
        return

    for i in range(0, len(codes), LOT):
        donnees = collect.fetch_json(
            URL, {"code_insee": ",".join(codes[i : i + LOT]), "page_size": 100}
        )
        if donnees is None:
            print(f"  API indisponible, relance geo_risque.py {DEPT} pour reprendre", flush=True)
            conn.close()
            sys.exit(1)
        chunk = [ligne for com in donnees.get("data", []) for ligne in clean.clean_risques(com)]
        load.insert_chunk(cur, "geo_risque", chunk)
        conn.commit()  # commit par lot : un run interrompu conserve les lots validés
        time.sleep(PAUSE)

    print(f"geo_risque: {load.count_rows(cur, 'geo_risque', DEPT)}", flush=True)
    conn.close()


if __name__ == "__main__":
    main()
