from pydantic import parse_obj_as

from pcapi import settings
from pcapi.connectors.serialization.cine_digital_service_serializers import CreateTransactionBodyCDS
from pcapi.connectors.serialization.cine_digital_service_serializers import CreateTransactionResponseCDS
from pcapi.connectors.serialization.cine_digital_service_serializers import ShowCDS
import pcapi.core.booking_providers.cds.exceptions as cds_exceptions
from pcapi.core.booking_providers.cds.mocked_api_calls import MockedCreateTransaction
from pcapi.core.booking_providers.cds.mocked_api_calls import MockedShows
from pcapi.utils import requests


def get_shows(cinema_id: str, url: str, token: str) -> list[ShowCDS]:

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
    shows = parse_obj_as(list[ShowCDS], json_response)

    return shows


def create_transaction(cinema_id: str, url: str, token: str, body: CreateTransactionBodyCDS) -> list[str]:
    api_url = f"https://{cinema_id}.{url}transaction/create?api_token={token}"

    try:
        if not settings.IS_DEV:
            headers = ({"Content-Type": "application/json"},)
            api_response = requests.post(api_url, headers=headers, data=body.json())
        else:
            api_response = MockedCreateTransaction()

    except Exception:
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Error connecting CDS for cinemaId={cinema_id} & url={url}"
        )
    print("id", body.ticketsaleCollection[0].showid)
    if api_response.status_code == 401:
        if api_response.text == "SHOW_NOT_FOUND":
            raise cds_exceptions.CineDigitalServiceAPIException(
                f"Show {body.ticketsaleCollection[0].showid} not found Cine digital Service API cinemaId={cinema_id} & url={url}"
            )
        if api_response.text == "INCORRECT_SEATING":
            raise cds_exceptions.CineDigitalServiceAPIException(
                f"Incorrect seating Cine Digital Service API cinemaId=${cinema_id} & url={url}"
            )
    elif api_response.status_code != 200:
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Error getting Cine Digital Service API DATA for cinemaId={cinema_id} & url={url}"
        )

    json_response = api_response.json()
    create_transaction_response = parse_obj_as(CreateTransactionResponseCDS, json_response)

    barcodes = []
    for ticket in create_transaction_response.tickets:
        barcodes.append(ticket.barcode)

    return barcodes
