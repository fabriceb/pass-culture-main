import datetime
from unittest.mock import patch

import pytest

from pcapi.connectors.serialization.cine_digital_service_serializers import ShowCDS
from pcapi.core.booking_providers.cds.CineDigitalService import CineDigitalServiceAPI
import pcapi.core.booking_providers.cds.exceptions as cds_exceptions


class CineDigitalServiceGetShowTest:
    @patch("pcapi.core.booking_providers.cds.CineDigitalService.get_shows")
    def test_should_return_show_corresponding_to_show_id(self, mocked_get_shows):
        shows = [
            ShowCDS(
                id=1,
                internet_remaining_place=10,
                showtime=datetime.datetime(2022, 3, 28),
                is_cancelled=False,
                is_deleted=False,
            ),
            ShowCDS(
                id=2,
                internet_remaining_place=30,
                showtime=datetime.datetime(2022, 3, 29),
                is_cancelled=False,
                is_deleted=False,
            ),
            ShowCDS(
                id=3,
                internet_remaining_place=100,
                showtime=datetime.datetime(2022, 3, 30),
                is_cancelled=False,
                is_deleted=False,
            ),
        ]
        mocked_get_shows.return_value = shows
        cine_digital_service = CineDigitalServiceAPI(cinemaid="cinemaid_test", token="token_test", apiUrl="apiUrl_test")
        show = cine_digital_service.get_show(2)

        assert show.id == 2

    @patch("pcapi.core.booking_providers.cds.CineDigitalService.get_shows")
    def test_should_raise_exception_if_show_not_found(self, mocked_get_shows):
        shows = [
            ShowCDS(
                id=1,
                internet_remaining_place=10,
                showtime=datetime.datetime(2022, 3, 28),
                is_cancelled=False,
                is_deleted=False,
            ),
            ShowCDS(
                id=2,
                internet_remaining_place=30,
                showtime=datetime.datetime(2022, 3, 29),
                is_cancelled=False,
                is_deleted=False,
            ),
            ShowCDS(
                id=3,
                internet_remaining_place=100,
                showtime=datetime.datetime(2022, 3, 30),
                is_cancelled=False,
                is_deleted=False,
            ),
        ]
        mocked_get_shows.return_value = shows
        cine_digital_service = CineDigitalServiceAPI(cinemaid="test_id", token="token_test", apiUrl="test_url")
        with pytest.raises(cds_exceptions.CineDigitalServiceAPIException) as cds_exception:
            cine_digital_service.get_show(4)
        assert (
            str(cds_exception.value)
            == "Show #4 not found in Cine Digital Service API for cinemaId=test_id & url=test_url"
        )


class CineDigitalServiceCreateTransactionTest:
    @patch("pcapi.core.booking_providers.cds.CineDigitalService.create_transaction")
    def test_should_call_connector_with_correct_args_and_return_barcodes(self, mocked_create_transaction):
        mocked_create_transaction.return_value = ["141414141414", "252525252525"]

        cine_digital_service = CineDigitalServiceAPI(cinemaid="test_id", token="token_test", apiUrl="test_url")
        barcodes = cine_digital_service.create_booking(show_id=14, quantity=2, amount=10)

        create_transaction_body_arg_call = mocked_create_transaction.call_args_list[0][0][3]

        assert create_transaction_body_arg_call.cinemaid == "test_id"
        assert len(create_transaction_body_arg_call.ticketsaleCollection) == 2
        assert create_transaction_body_arg_call.ticketsaleCollection[0].id == -1
        assert create_transaction_body_arg_call.ticketsaleCollection[0].showid.id == 14
        assert create_transaction_body_arg_call.ticketsaleCollection[0].tariffid.id == 32
        assert create_transaction_body_arg_call.ticketsaleCollection[1].id == -2
        assert len(create_transaction_body_arg_call.paiementCollection) == 1
        assert create_transaction_body_arg_call.paiementCollection[0].id == -1
        assert create_transaction_body_arg_call.paiementCollection[0].amount == 20
        assert create_transaction_body_arg_call.paiementCollection[0].paiementtypeid.id == 4

        assert barcodes == ["141414141414", "252525252525"]

    def test_should_raise_exception_when_quantity_is_greater_then_two(self):
        cine_digital_service = CineDigitalServiceAPI(cinemaid="test_id", token="token_test", apiUrl="test_url")

        with pytest.raises(Exception) as exception:
            cine_digital_service.create_booking(show_id=14, quantity=3, amount=10)

        assert str(exception.value) == "Booking quantity should be 1 or 2"
