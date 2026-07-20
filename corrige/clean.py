"""Nettoyage : une ligne brute (API ou CSV) vers un dict prêt à insérer.

Les clés des dicts sont les colonnes SQL des tables cibles.
"""

# geo.api.gouv.fr ne liste pas les arrondissements municipaux de Lyon (9),
# Paris (20) et Marseille (16) : chaque code d'arrondissement est ramené au
# code de la commune principale. Les fichiers DVF emploient les codes
# d'arrondissement.
DISTRICTS = {}
DISTRICTS.update({str(c): "69123" for c in range(69381, 69390)})  # Lyon
DISTRICTS.update({str(c): "75056" for c in range(75101, 75121)})  # Paris
DISTRICTS.update({str(c): "13055" for c in range(13201, 13217)})  # Marseille


def normalize_insee(code):
    code = str(code).strip()
    return DISTRICTS.get(code, code)


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def clean_qualite(row):
    """Une mesure de resultats_dis."""
    code_prelevement = row.get("code_prelevement")
    code_parametre = row.get("code_parametre")
    reseaux = [
        {"code_reseau": r["code"], "nom_reseau": r.get("nom")}
        for r in (row.get("reseaux") or [])
        if r.get("code")
    ]
    return {
        "identifiant": f"{code_prelevement}-{code_parametre}"
        if code_prelevement and code_parametre
        else None,
        "code_prelevement": code_prelevement,
        "libelle_parametre": row.get("libelle_parametre"),
        "resultat_alphanumerique": row.get("resultat_alphanumerique"),
        "resultat_numerique": _to_float(row.get("resultat_numerique")),
        "libelle_unite": row.get("libelle_unite"),
        "date_prelevement": row.get("date_prelevement"),
        "conclusion_conformite": row.get("conclusion_conformite_prelevement"),
        # code brut conservé : sert à la réaffectation des lignes en sentinelle
        "code_commune_source": row.get("code_commune"),
        "insee_code": normalize_insee(row.get("code_commune")),
        # liste consommée par insert_reseaux, pas une colonne de la table
        "reseaux": reseaux,
    }


def clean_udi(row):
    """Une ligne de communes_udi : le rattachement d'une commune à un réseau."""
    return {
        "insee_code": normalize_insee(row.get("code_commune")),
        "code_reseau": row.get("code_reseau"),
        "annee": row.get("annee"),
        "nom_reseau": row.get("nom_reseau"),
        "debut_alim": row.get("debut_alim") or None,
    }


def clean_risques(commune_gaspar):
    """Aplatit ("flatten") une entrée GASPAR en une ligne par (commune, risque).

    La réponse de l'API est imbriquée : une entrée par commune, portant la
    liste risques_detail.
    """
    insee = normalize_insee(commune_gaspar.get("code_insee"))
    return [
        {
            "insee_code": insee,
            "num_risque": r["num_risque"],
            "libelle_risque_long": r.get("libelle_risque_long"),
        }
        for r in commune_gaspar.get("risques_detail") or []
        if r.get("num_risque")
    ]
