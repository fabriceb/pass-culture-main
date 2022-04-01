from datetime import datetime
from datetime import timedelta
from datetime import timezone
import json
from unittest import mock

import pytest

from pcapi.connectors.cine_digital_service import create_transaction
from pcapi.connectors.cine_digital_service import get_shows
from pcapi.connectors.serialization.cine_digital_service_serializers import CreateTransactionBodyCDS
from pcapi.connectors.serialization.cine_digital_service_serializers import IdObjectCDS
from pcapi.connectors.serialization.cine_digital_service_serializers import PaiementCDS
from pcapi.connectors.serialization.cine_digital_service_serializers import TicketSaleCDS
import pcapi.core.booking_providers.cds.exceptions as cds_exceptions
from pcapi.core.testing import override_settings


class CineDigitalServiceGetShowsTest:
    @mock.patch("pcapi.connectors.cine_digital_service.requests.get")
    @override_settings(IS_DEV=False)
    def test_should_return_all_necessary_attributes(self, request_get):
        # Given
        cinema_id = "test_id"
        url = "test_url"
        token = "test_token"
        shows_json = [
            {
                "id": 1,
                "internetremainingplace": 10,
                "showtime": "2022-03-28T09:00:00.000+0100",
                "canceled": True,
                "deleted": False,
            },
        ]

        response_return_value = mock.MagicMock(status_code=200, text="")
        response_return_value.json = mock.MagicMock(return_value=shows_json)
        request_get.return_value = response_return_value

        # When
        shows = get_shows(cinema_id, url, token)

        # Then
        assert len(shows) == 1
        assert shows[0].id == 1
        assert shows[0].internet_remaining_place == 10
        assert shows[0].showtime == datetime(2022, 3, 28, 9, tzinfo=timezone(timedelta(seconds=3600)))
        assert shows[0].is_cancelled
        assert not shows[0].is_deleted

    @mock.patch("pcapi.connectors.cine_digital_service.requests.get")
    @override_settings(IS_DEV=False)
    def test_should_return_shows_with_success(self, request_get):
        # Given
        cinema_id = "test_id"
        url = "test_url"
        token = "test_token"
        shows_json = [
            {
                "id": 1,
                "internetremainingplace": 10,
                "showtime": "2022-03-28T09:00:00.000+0100",
                "canceled": False,
                "deleted": False,
            },
            {
                "id": 2,
                "internetremainingplace": 30,
                "showtime": "2022-03-30T18:00:00.000+0100",
                "canceled": True,
                "deleted": False,
            },
        ]

        response_return_value = mock.MagicMock(status_code=200, text="")
        response_return_value.json = mock.MagicMock(return_value=shows_json)
        request_get.return_value = response_return_value

        # When
        shows = get_shows(cinema_id, url, token)

        # Then
        request_get.assert_called_once_with(f"https://{cinema_id}.{url}shows?api_token={token}")
        assert len(shows) == 2

    @mock.patch("pcapi.connectors.cine_digital_service.requests.get")
    @override_settings(IS_DEV=False)
    def test_should_raise_exception_when_api_call_fails(self, request_get):
        # Given
        cinema_id = "test_id"
        url = "test_url"
        token = "test_token"
        response_return_value = mock.MagicMock(status_code=400, text="")
        request_get.return_value = response_return_value

        # When
        with pytest.raises(cds_exceptions.CineDigitalServiceAPIException) as exception:
            get_shows(cinema_id, url, token)

        # Then
        assert (
            str(exception.value) == f"Error getting Cine Digital Service API DATA for cinemaId={cinema_id} & url={url}"
        )

    @mock.patch("pcapi.connectors.cine_digital_service.requests.get", side_effect=Exception)
    @override_settings(IS_DEV=False)
    def test_should_raise_exception_when_api_call_fails_with_connection_error(self, request_get):
        # Given
        cinema_id = "test_id"
        url = "test_url"
        token = "test_token"

        # When
        with pytest.raises(cds_exceptions.CineDigitalServiceAPIException) as cds_exception:
            get_shows(cinema_id, url, token)

        # Then
        assert str(cds_exception.value) == f"Error connecting CDS for cinemaId={cinema_id} & url={url}"


class CineDigitalServiceCreateTransactionTest:
    @staticmethod
    def _create_transaction_body():
        tariffid = IdObjectCDS(id=1)
        showid = IdObjectCDS(id=1)
        paiementtypeid = IdObjectCDS(id=1)
        ticket_sale = TicketSaleCDS(
            id=-1,
            cinemaid="test_id",
            operationdate="2022-04-08T14:58:57.223+01:00",
            canceled=True,
            tariffid=tariffid,
            showid=showid,
            disabledperson=False,
        )
        paiement = PaiementCDS(id=1, amount=5, paiementtypeid=paiementtypeid)
        return CreateTransactionBodyCDS(
            transactiondate="2022-04-08T14:58:57.223+01:00",
            canceled=False,
            cinemaid="test_id",
            ticketsaleCollection=[ticket_sale],
            paiementCollection=[paiement],
        )

    @mock.patch("pcapi.connectors.cine_digital_service.requests.post")
    @override_settings(IS_DEV=False)
    def test_should_return_create_transaction_body_object(self, mocked_request_post):
        cinema_id = "test_id"
        url = "test_url"
        token = "test_token"

        create_transaction_json_response = {
            "id": 1111,
            "invoiceid": "2222",
            "tickets": [
                {
                    "barcode": "5555555555555",
                }
            ],
        }

        response_return_value = mock.MagicMock(status_code=200)
        response_return_value.json = mock.MagicMock(return_value=create_transaction_json_response)
        mocked_request_post.return_value = response_return_value

        body = self._create_transaction_body()

        response = create_transaction(cinema_id, url, token, body)

        post_call_data_arg = mocked_request_post.call_args[1]["data"]
        expected_body_json = {
            "cinemaid": "test_id",
            "transactiondate": "2022-04-08T14:58:57.223+01:00",
            "canceled": False,
            "ticketsaleCollection": [
                {
                    "id": -1,
                    "cinemaid": "test_id",
                    "operationdate": "2022-04-08T14:58:57.223+01:00",
                    "canceled": True,
                    "tariffid": {"id": 1},
                    "showid": {"id": 1},
                    "disabledperson": False,
                }
            ],
            "paiementCollection": [{"id": 1, "amount": 5.0, "paiementtypeid": {"id": 1}}],
        }

        assert json.loads(post_call_data_arg) == expected_body_json

        assert len(response) == 1
        assert response == ["5555555555555"]

    @mock.patch("pcapi.connectors.cine_digital_service.requests.post")
    @override_settings(IS_DEV=False)
    def test_should_raise_exception_when_show_not_found(self, mocked_request_post):
        cinema_id = "test_id"
        url = "test_url"
        token = "test_token"
        show_id = 1478

        response_return_value = mock.MagicMock(status_code=401, text="SHOW_NOT_FOUND")
        mocked_request_post.return_value = response_return_value
        body = self._create_transaction_body()
        body.ticketsaleCollection[0].showid.id = show_id

        with pytest.raises(cds_exceptions.CineDigitalServiceAPIException) as cds_exception:
            create_transaction(cinema_id, url, token, body)

        assert (
            str(cds_exception.value)
            == f"Show id={show_id} not found Cine digital Service API cinemaId={cinema_id} & url={url}"
        )
