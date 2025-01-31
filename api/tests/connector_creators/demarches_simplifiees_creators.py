from typing import Optional


def offerer_demarche_simplifiee_application_detail_response(
    siren: str,
    bic: Optional[str],
    iban: Optional[str],
    idx: int = 1,
    updated_at: str = "2020-01-21T18:55:03.387Z",
    state: str = "closed",
) -> dict:
    return {
        "dossier": {
            "id": idx,
            "updated_at": updated_at,
            "state": state,
            "entreprise": {
                "siren": siren,
            },
            "champs": [
                {
                    "value": bic,
                    "type_de_champ": {
                        "id": 352727,
                        "libelle": "BIC",
                        "type_champ": "text",
                        "order_place": 8,
                        "description": "",
                    },
                },
                {
                    "value": iban,
                    "type_de_champ": {
                        "id": 352722,
                        "libelle": "IBAN",
                        "type_champ": "text",
                        "order_place": 9,
                        "description": "",
                    },
                },
            ],
        }
    }


def venue_demarche_simplifiee_application_detail_response_with_siret(
    siret: str,
    bic: Optional[str],
    iban: Optional[str],
    idx: int = 1,
    updated_at: str = "2020-01-21T18:55:03.387Z",
    siren: Optional[str] = None,
    state: str = "closed",
) -> dict:
    return {
        "dossier": {
            "id": idx,
            "updated_at": updated_at,
            "state": state,
            "entreprise": {
                "siren": siren or siret[0:9],
            },
            "etablissement": {
                "siret": siret,
            },
            "champs": [
                {
                    "value": siret,
                    "type_de_champ": {
                        "id": 782800,
                        "libelle": "Si vous souhaitez renseigner les coordonn\u00e9es bancaires d'un lieu avec SIRET, merci de saisir son SIRET :",
                    },
                    "etablissement": {
                        "siret": siret,
                    },
                    "entreprise": {
                        "siren": siret[0:9],
                    },
                },
                {
                    "value": "",
                    "type_de_champ": {
                        "id": 909032,
                        "libelle": "Si vous souhaitez renseigner les coordonn\\u00e9es bancaires d'un lieu sans SIRET, merci de saisir le \"Nom du lieu\", \\u00e0 l'identique de celui dans le pass Culture Pro :",
                    },
                },
                {
                    "value": iban,
                    "type_de_champ": {
                        "id": 352722,
                        "libelle": "IBAN",
                    },
                },
                {
                    "value": bic,
                    "type_de_champ": {
                        "id": 352727,
                        "libelle": "BIC",
                    },
                },
            ],
        }
    }


def venue_demarche_simplifiee_application_detail_response_without_siret(
    siret: str,
    bic: Optional[str],
    iban: Optional[str],
    idx: int = 1,
    updated_at: str = "2020-01-21T18:55:03.387Z",
    state: str = "closed",
) -> dict:
    return {
        "dossier": {
            "id": idx,
            "updated_at": updated_at,
            "state": state,
            "entreprise": {
                "siren": siret[0:9],
            },
            "etablissement": {
                "siret": siret,
            },
            "champs": [
                {
                    "value": "",
                    "type_de_champ": {
                        "id": 782800,
                        "libelle": "Si vous souhaitez renseigner les coordonn\u00e9es bancaires d'un lieu avec SIRET, merci de saisir son SIRET :",
                    },
                    "etablissement": None,
                    "entreprise": None,
                },
                {
                    "value": "VENUE_NAME",
                    "type_de_champ": {
                        "id": 909032,
                        "libelle": "Si vous souhaitez renseigner les coordonn\u00e9es bancaires d'un lieu sans SIRET, merci de saisir le \"Nom du lieu\", \u00e0 l'identique de celui dans le pass Culture Pro :",
                    },
                },
                {
                    "value": iban,
                    "type_de_champ": {
                        "id": 352722,
                        "libelle": "IBAN",
                    },
                },
                {
                    "value": bic,
                    "type_de_champ": {
                        "id": 352727,
                        "libelle": "BIC",
                    },
                },
            ],
        }
    }


def venue_demarche_simplifiee_get_bic_response_v2(annotation: dict):
    return {
        "dossier": {
            "id": "Q2zzbXAtNzgyODAw",
            "champs": [
                {
                    "etablissement": {
                        "entreprise": {
                            "siren": "123456789",
                        },
                        "siret": "12345678900014",
                    },
                    "id": "Q2hhbXAtNzgyODAw",
                    "label": "SIRET",
                    "stringValue": "12345678900014",
                },
                {"id": "Q2hhbXAtNzAwNTA5", "label": "Vos coordonnées bancaires", "stringValue": "", "value": None},
                {
                    "id": "Q2hhbXAtMzUyNzIy",
                    "label": "IBAN",
                    "stringValue": "FR7630007000111234567890144",
                    "value": "FR7630007000111234567890144",
                },
                {"id": "Q2hhbXAtMzUyNzI3", "label": "BIC", "stringValue": "SOGEFRPP", "value": "SOGEFRPP"},
            ],
            "dateDerniereModification": "2020-01-03T01:00:00+01:00",
            "state": "accepte",
            "annotations": [annotation],
        },
    }
