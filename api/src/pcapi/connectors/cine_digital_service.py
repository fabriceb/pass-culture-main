from pydantic import parse_obj_as

from pcapi import settings
import pcapi.connectors.serialization.cine_digital_service_serializers as cds_serializers
import pcapi.core.booking_providers.cds.exceptions as cds_exceptions
from pcapi.core.booking_providers.cds.mocked_api_calls import MockedCancelBookingSuccess
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


def cancel_booking(cinema_id: str, url: str, token: str, body: cds_serializers.CancelBookingCDS):
    api_url = f"https://{cinema_id}.{url}transaction/cancel?api_token={token}"
    try:
        if not settings.IS_DEV:
            headers = ({"Content-Type": "application/json"},)
            api_response = requests.put(api_url, headers=headers, data=body.json())
        else:
            api_response = MockedCancelBookingSuccess
    except Exception:
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Error connecting CDS for cinemaId={cinema_id} & url={url}"
        )
    if api_response.status_code != 200:
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Error while canceling booking in Cine Digital Service API DATA for cinemaId={cinema_id} & url={url}"
        )

    json_response = api_response.json()

    if api_response.status_code == 200 and json_response:
        cancel_errors = parse_obj_as(cds_serializers.CancelBookingsErrorsCDS, json_response)
        print(cancel_errors.__root__)
        sep = "\n"
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Error while canceling bookings :{sep}{sep.join([f'{barcode} : {error_msg}' for barcode, error_msg in cancel_errors.__root__.items()])}"
        )
