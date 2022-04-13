import datetime
from unittest import mock

import pytest

from pcapi.connectors.cine_digital_service import build_url
from pcapi.connectors.cine_digital_service import get_resource
from pcapi.connectors.cine_digital_service import parse_json_data
import pcapi.connectors.serialization.cine_digital_service_serializers as cds_serializers
import pcapi.core.booking_providers.cds.exceptions as cds_exceptions
from pcapi.core.booking_providers.cds.mocked_api_calls import MockedShows
from pcapi.core.testing import override_settings


class CineDigitalServiceBuildUrlTest:
    def test_build_url(self):
        cinema_id = "test_id"
        url = "test_url/"
        token = "test_token"
        resource = "tariffs"

        url = build_url(cinema_id, url, token, resource)

        assert url == "https://test_id.test_url/tariffs?api_token=test_token"


class CineDigitalServiceGetResourceTest:
    @mock.patch("pcapi.connectors.cine_digital_service.requests.get")
    @override_settings(IS_DEV=False)
    def test_should_return_shows_with_success(self, request_get):
        # Given
        url = "test_url"

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
        json_data = get_resource(url, None)

        # Then
        request_get.assert_called_once_with(url)
        assert json_data == shows_json

    @mock.patch("pcapi.connectors.cine_digital_service.requests.get")
    @override_settings(IS_DEV=False)
    def test_should_raise_exception_when_api_call_fails(self, request_get):
        # Given
        response_return_value = mock.MagicMock(status_code=400, text="")
        request_get.return_value = response_return_value
        url = "test"

        # When
        with pytest.raises(cds_exceptions.CineDigitalServiceAPIException) as exception:
            get_resource(url, MockedShows)

        # Then
        assert str(exception.value) == f"Error getting Cine Digital Service API DATA - url : {url}"


class CineDigitalServiceParseJsonDataTest:
    def test_should_return_pydantic_data(self):

        # given
        json_data = [
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

        serializer = cds_serializers.ShowCDS

        data = parse_json_data(json_data, serializer)

        assert data == [
            cds_serializers.ShowCDS(
                id=1,
                internet_remaining_place=10,
                showtime=datetime.datetime(
                    2022, 3, 28, 9, 0, tzinfo=datetime.timezone(datetime.timedelta(seconds=3600))
                ),
                is_cancelled=False,
                is_deleted=False,
            ),
            cds_serializers.ShowCDS(
                id=2,
                internet_remaining_place=30,
                showtime=datetime.datetime(
                    2022, 3, 30, 18, 0, tzinfo=datetime.timezone(datetime.timedelta(seconds=3600))
                ),
                is_cancelled=True,
                is_deleted=False,
            ),
        ]
