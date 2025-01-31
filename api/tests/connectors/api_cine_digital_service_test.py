from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest import mock

import pytest

from pcapi.connectors.cine_digital_service import get_payment_types
from pcapi.connectors.cine_digital_service import get_screens
from pcapi.connectors.cine_digital_service import get_shows
from pcapi.connectors.cine_digital_service import get_tariffs
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


class CineDigitalServiceGetPaymentTypesTest:
    @mock.patch("pcapi.connectors.cine_digital_service.requests.get")
    @override_settings(IS_DEV=False)
    def test_should_return_all_necessary_attributes(self, request_get):
        # Given
        cinema_id = "test_id"
        url = "test_url"
        token = "test_token"
        payment_types_json = [
            {"id": 1, "active": True, "shortlabel": "PASSCULTURE"},
        ]

        response_return_value = mock.MagicMock(status_code=200, text="")
        response_return_value.json = mock.MagicMock(return_value=payment_types_json)
        request_get.return_value = response_return_value

        # When
        payment_types = get_payment_types(cinema_id, url, token)

        # Then
        assert len(payment_types) == 1
        assert payment_types[0].id == 1
        assert payment_types[0].is_active
        assert payment_types[0].short_label == "PASSCULTURE"

    @mock.patch("pcapi.connectors.cine_digital_service.requests.get")
    @override_settings(IS_DEV=False)
    def test_should_return_shows_with_success(self, request_get):
        # Given
        cinema_id = "test_id"
        url = "test_url"
        token = "test_token"
        payment_types_json = [
            {"id": 1, "active": True, "shortlabel": "PASSCULTURE"},
            {"id": 2, "active": True, "shortlabel": "CHEQUEVACANCES"},
        ]

        response_return_value = mock.MagicMock(status_code=200, text="")
        response_return_value.json = mock.MagicMock(return_value=payment_types_json)
        request_get.return_value = response_return_value

        # When
        payment_types = get_payment_types(cinema_id, url, token)

        # Then
        request_get.assert_called_once_with(f"https://{cinema_id}.{url}paiementtype?api_token={token}")
        assert len(payment_types) == 2

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
            get_payment_types(cinema_id, url, token)
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
            get_payment_types(cinema_id, url, token)
        # Then
        assert str(cds_exception.value) == f"Error connecting CDS for cinemaId={cinema_id} & url={url}"


class CineDigitalServiceGetTariffsTest:
    @mock.patch("pcapi.connectors.cine_digital_service.requests.get")
    @override_settings(IS_DEV=False)
    def test_should_return_all_necessary_attributes(self, request_get):
        # Given
        cinema_id = "test_id"
        url = "test_url"
        token = "test_token"

        tariffs_json = [
            {
                "id": 1,
                "labeltariff": "Pass Culture 5€",
                "price": 3.5,
                "active": True,
            },
        ]

        response_return_value = mock.MagicMock(status_code=200, text="")
        response_return_value.json = mock.MagicMock(return_value=tariffs_json)
        request_get.return_value = response_return_value

        # When
        tariffs = get_tariffs(cinema_id, url, token)

        # Then
        assert len(tariffs) == 1
        assert tariffs[0].id == 1
        assert tariffs[0].label == "Pass Culture 5€"
        assert tariffs[0].price == 3.5
        assert tariffs[0].is_active

    @mock.patch("pcapi.connectors.cine_digital_service.requests.get")
    @override_settings(IS_DEV=False)
    def test_should_return_shows_with_success(self, request_get):
        # Given
        cinema_id = "test_id"
        url = "test_url"
        token = "test_token"
        tariffs_json = [
            {
                "id": 1,
                "labeltariff": "Pass Culture 5€",
                "price": 3.5,
                "active": True,
            },
            {
                "id": 2,
                "labeltariff": "Another tariff",
                "price": 10,
                "active": True,
            },
        ]

        response_return_value = mock.MagicMock(status_code=200, text="")
        response_return_value.json = mock.MagicMock(return_value=tariffs_json)
        request_get.return_value = response_return_value

        # When
        shows = get_tariffs(cinema_id, url, token)

        # Then
        request_get.assert_called_once_with(f"https://{cinema_id}.{url}tariffs?api_token={token}")
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
            get_tariffs(cinema_id, url, token)

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
            get_tariffs(cinema_id, url, token)

        # Then
        assert str(cds_exception.value) == f"Error connecting CDS for cinemaId={cinema_id} & url={url}"


class CineDigitalServiceGetScreensTest:
    @mock.patch("pcapi.connectors.cine_digital_service.requests.get")
    @override_settings(IS_DEV=False)
    def test_should_return_all_necessary_attributes(self, request_get):
        # Given
        cinema_id = "test_id"
        url = "test_url"
        token = "test_token"
        screen_json = [
            {
                "id": 1,
                "seatmapfronttoback": False,
                "seatmaplefttoright": True,
                "seatmapskipmissingseats": True,
            },
        ]

        response_return_value = mock.MagicMock(status_code=200, text="")
        response_return_value.json = mock.MagicMock(return_value=screen_json)
        request_get.return_value = response_return_value

        # When
        screens = get_screens(cinema_id, url, token)

        # Then
        assert len(screens) == 1
        assert screens[0].id == 1
        assert not screens[0].seatmap_front_to_back
        assert screens[0].seatmap_left_to_right
        assert screens[0].seatmap_skip_missing_seats

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
                "seatmapfronttoback": False,
                "seatmaplefttoright": True,
                "seatmapskipmissingseats": True,
            },
            {
                "id": 2,
                "seatmapfronttoback": True,
                "seatmaplefttoright": False,
                "seatmapskipmissingseats": True,
            },
        ]

        response_return_value = mock.MagicMock(status_code=200, text="")
        response_return_value.json = mock.MagicMock(return_value=shows_json)
        request_get.return_value = response_return_value

        # When
        screens = get_screens(cinema_id, url, token)

        # Then
        request_get.assert_called_once_with(f"https://{cinema_id}.{url}screens?api_token={token}")
        assert len(screens) == 2

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
            get_screens(cinema_id, url, token)

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
            get_screens(cinema_id, url, token)

        # Then
        assert str(cds_exception.value) == f"Error connecting CDS for cinemaId={cinema_id} & url={url}"
