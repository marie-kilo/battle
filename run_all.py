"""Orchestration : les 4 collecteurs sur une liste de départements.

Usage : python3 run_all.py (les 101 départements)
             python3 run_all.py 69 01 (une sélection)

Chaque script de collecte implémente sa propre reprise.
Code de sortie : 0 sans échec, 1 sinon.
"""

import subprocess
import sys

# 101 départements : 96 métropolitains (2A et 2B remplacent le 20) et
# 5 d'outre-mer (971 à 974 et 976).
DEPARTEMENTS = [
    "01",
    "02",
    "03",
    "04",
    "05",
    "06",
    "07",
    "08",
    "09",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "16",
    "17",
    "18",
    "19",
    "2A",
    "2B",
    "21",
    "22",
    "23",
    "24",
    "25",
    "26",
    "27",
    "28",
    "29",
    "30",
    "31",
    "32",
    "33",
    "34",
    "35",
    "36",
    "37",
    "38",
    "39",
    "40",
    "41",
    "42",
    "43",
    "44",
    "45",
    "46",
    "47",
    "48",
    "49",
    "50",
    "51",
    "52",
    "53",
    "54",
    "55",
    "56",
    "57",
    "58",
    "59",
    "60",
    "61",
    "62",
    "63",
    "64",
    "65",
    "66",
    "67",
    "68",
    "69",
    "70",
    "71",
    "72",
    "73",
    "74",
    "75",
    "76",
    "77",
    "78",
    "79",
    "80",
    "81",
    "82",
    "83",
    "84",
    "85",
    "86",
    "87",
    "88",
    "89",
    "90",
    "91",
    "92",
    "93",
    "94",
    "95",
    "971",
    "972",
    "973",
    "974",
    "976",
]

SCRIPTS = ["geo_risque.py", "reseau_eau.py", "qualite_eau.py", "dvf.py"]


def main():
    depts = [d.upper().zfill(2) for d in sys.argv[1:]] or DEPARTEMENTS
    echecs = []
    for dept in depts:
        for script in SCRIPTS:
            res = subprocess.run([sys.executable, script, dept])
            if res.returncode != 0:
                echecs.append(f"{script} {dept}")

    if echecs:
        print(f"{len(echecs)} échec(s) : {', '.join(echecs)}", flush=True)
        sys.exit(1)
    print(f"{len(depts)} département(s) chargés sans échec", flush=True)


if __name__ == "__main__":
    main()
