import enum

from pydantic import parse_obj_as

from pcapi import settings
import pcapi.core.booking_providers.cds.exceptions as cds_exceptions
from pcapi.utils import requests


class resourceCDS(enum.Enum):
    TARIFFS = "tariffs"
    SHOWS = "shows"
    PAYMENT_TYPE = "paiementtype"
    SCREENS = "screens"


def build_url(cinema_id: str, url: str, token: str, resource: str) -> str:
    return f"https://{cinema_id}.{url}{resource}?api_token={token}"


def get_resource(url, mocked_resource: object):

    try:
        if not settings.IS_DEV:
            api_response = requests.get(url)
        else:
            api_response = mocked_resource()
    except Exception:
        raise cds_exceptions.CineDigitalServiceAPIException(f"Error connecting CDS - url : {url}")

    if api_response.status_code != 200:
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Error getting Cine Digital Service API DATA - url : {url}"
        )

    return api_response.json()


def parse_json_data(json_data: str, serializer: object):
    return parse_obj_as(list[serializer], json_data)
