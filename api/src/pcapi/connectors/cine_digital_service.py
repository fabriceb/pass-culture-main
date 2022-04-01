from pydantic import parse_obj_as

from pcapi import settings
import pcapi.connectors.serialization.cine_digital_service_serializers as cds_serializers
import pcapi.core.booking_providers.cds.exceptions as cds_exceptions
from pcapi.core.booking_providers.cds.mocked_api_calls import MockedScreens
from pcapi.core.booking_providers.cds.mocked_api_calls import MockedSeatMap
from pcapi.core.booking_providers.cds.mocked_api_calls import MockedShows
from pcapi.utils import requests


def get_shows(cinema_id: str, url: str, token: str) -> list[cds_serializers.ShowCDS]:

    api_url = f"https://{cinema_id}.{url}shows?api_token={token}"

    try:
        if not settings.IS_DEV:
            api_response = requests.get(api_url)
        else:
            api_response = MockedShows()
    except Exception:
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Error connecting CDS for cinemaId={cinema_id} & url={url}"
        )

    if api_response.status_code != 200:
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Error getting Cine Digital Service API DATA for cinemaId={cinema_id} & url={url}"
        )

    json_response = api_response.json()
    shows = parse_obj_as(list[cds_serializers.ShowCDS], json_response)

    return shows


def get_screens(cinema_id: str, url: str, token: str) -> list[cds_serializers.ShowCDS]:

    api_url = f"https://{cinema_id}.{url}screens?api_token={token}"

    try:
        if not settings.IS_DEV:
            api_response = requests.get(api_url)
        else:
            api_response = MockedScreens()
    except Exception:
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Error connecting CDS for cinemaId={cinema_id} & url={url}"
        )

    if api_response.status_code != 200:
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Error getting Cine Digital Service API DATA for cinemaId={cinema_id} & url={url}"
        )

    json_response = api_response.json()
    screens = parse_obj_as(list[cds_serializers.ScreenCDS], json_response)

    return screens


def get_seatmap(cinema_id: str, url: str, show_id: int, token: str):
    api_url = f"https://{cinema_id}.{url}shows/{show_id}/seatmap?api_token={token}"
    try:
        if not settings.IS_DEV:
            api_response = requests.get(api_url)
        else:
            api_response = MockedSeatMap()
    except Exception:
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Error connecting CDS for cinemaId={cinema_id} & url={url}"
        )

    if api_response.status_code != 200:
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Error getting Cine Digital Service API DATA for cinemaId={cinema_id} & url={url}"
        )

    json_response = api_response.json()
    seatmap = parse_obj_as(cds_serializers.SeatmapCDS, json_response)
    if seatmap.nb_row == 0:
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Seatmap not found in Cine Digital Service API for show #{show_id}, cinemaId={cinema_id} & url={url}"
        )
    return seatmap
