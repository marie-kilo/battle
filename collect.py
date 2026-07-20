"""Collecte : appels HTTP vers les APIs sources."""

import time

import requests

# Hub'Eau coupe la connexion quand le User-Agent par défaut de requests est
# utilisé : un User-Agent explicite est déclaré sur la session.
session = requests.Session()
session.headers["User-Agent"] = "megabase-corrige-battle (formation)"

GEO = "https://geo.api.gouv.fr/communes"

TENTATIVES = 10
ATTENTE = 60  # secondes ; le bridage Hub'Eau et Géorisques dure plusieurs minutes


def fetch_communes(dept):
    """Communes d'un département en 1 appel, avec département et région.

    - geo.api.gouv.fr refuse des connexions lors d'appels en rafale
    (constaté le 12 juillet 2026)
    - donc l'appel passe par fetch_json
    - l'éventuel échec final est signalé par exception
    """
    donnees = fetch_json(
        GEO,
        {
            "codeDepartement": dept,
            "fields": "nom,code,population,departement,region",
            "format": "json",
        },
        timeout=30,
    )
    if donnees is None:
        raise requests.ConnectionError("geo.api.gouv.fr indisponible")
    return donnees


def fetch_json(url, params, timeout=60):
    """Un appel JSON avec nouvelles tentatives en cas de bridage.

    - Hub'Eau et Géorisques coupent la connexion ou renvoient 503 au-delà de leur plafond de fréquence.
    - Chaque échec déclenche une attente de 60 s, 10 tentatives au plus.
    - Renvoie None si l'API reste indisponible : l'appelant s'arrête et la reprise couvre la relance.
    """
    for tentative in range(TENTATIVES):
        try:
            resp = session.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"  bridage ({type(e).__name__}), attente {ATTENTE} s", flush=True)
            time.sleep(ATTENTE)
    return None


def fetch_fichier(url, timeout=300):
    """Le contenu binaire d'un fichier HTTP, avec les mêmes tentatives.

    - une réponse 404 signale un fichier inexistant (cas normal pour les départements absents d'une source)
    - elle est renvoyée comme None sans nouvelle tentative
    - Les autres échecs suivent la politique de fetch_json, puis lèvent une exception
    """
    for tentative in range(TENTATIVES):
        try:
            resp = session.get(url, timeout=timeout)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as e:
            print(f"  bridage ({type(e).__name__}), attente {ATTENTE} s", flush=True)
            time.sleep(ATTENTE)
    raise requests.ConnectionError(f"{url} indisponible")
