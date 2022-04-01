import datetime
from unittest.mock import patch

import pytest

import pcapi.connectors.serialization.cine_digital_service_serializers as cds_serializers
from pcapi.core.booking_providers.cds.CineDigitalService import CineDigitalServiceAPI
import pcapi.core.booking_providers.cds.exceptions as cds_exceptions


class CineDigitalServiceGetShowTest:
    @patch("pcapi.core.booking_providers.cds.CineDigitalService.get_shows")
    def test_should_return_show_corresponding_to_show_id(self, mocked_get_shows):
        shows = [
            cds_serializers.ShowCDS(
                id=1,
                internet_remaining_place=10,
                showtime=datetime.datetime(2022, 3, 28),
                is_cancelled=False,
                is_deleted=False,
            ),
            cds_serializers.ShowCDS(
                id=2,
                internet_remaining_place=30,
                showtime=datetime.datetime(2022, 3, 29),
                is_cancelled=False,
                is_deleted=False,
            ),
            cds_serializers.ShowCDS(
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
            cds_serializers.ShowCDS(
                id=1,
                internet_remaining_place=10,
                showtime=datetime.datetime(2022, 3, 28),
                is_cancelled=False,
                is_deleted=False,
            ),
            cds_serializers.ShowCDS(
                id=2,
                internet_remaining_place=30,
                showtime=datetime.datetime(2022, 3, 29),
                is_cancelled=False,
                is_deleted=False,
            ),
            cds_serializers.ShowCDS(
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


class CineDigitalServiceGetScreenTest:
    @patch("pcapi.core.booking_providers.cds.CineDigitalService.get_screens")
    def test_should_return_screen_corresponding_to_screen_id(self, mocked_get_screens):
        screens = [
            cds_serializers.ScreenCDS(
                id=1,
                seatmapfronttoback=True,
                seatmaplefttoright=False,
                seatmapskipmissingseats=False,
            ),
            cds_serializers.ScreenCDS(
                id=2,
                seatmapfronttoback=False,
                seatmaplefttoright=True,
                seatmapskipmissingseats=True,
            ),
            cds_serializers.ScreenCDS(
                id=3,
                seatmapfronttoback=True,
                seatmaplefttoright=True,
                seatmapskipmissingseats=True,
            ),
        ]
        mocked_get_screens.return_value = screens
        cine_digital_service = CineDigitalServiceAPI(cinemaid="test_id", token="token_test", apiUrl="test_url")
        show = cine_digital_service.get_screen(2)

        assert show.id == 2

    @patch("pcapi.core.booking_providers.cds.CineDigitalService.get_screens")
    def test_should_raise_exception_if_screen_not_found(self, mocked_get_screens):
        screens = [
            cds_serializers.ScreenCDS(
                id=1,
                seatmapfronttoback=True,
                seatmaplefttoright=False,
                seatmapskipmissingseats=False,
            ),
            cds_serializers.ScreenCDS(
                id=2,
                seatmapfronttoback=False,
                seatmaplefttoright=True,
                seatmapskipmissingseats=True,
            ),
            cds_serializers.ScreenCDS(
                id=3,
                seatmapfronttoback=True,
                seatmaplefttoright=True,
                seatmapskipmissingseats=True,
            ),
        ]
        mocked_get_screens.return_value = screens
        cine_digital_service = CineDigitalServiceAPI(cinemaid="test_id", token="token_test", apiUrl="test_url")
        with pytest.raises(cds_exceptions.CineDigitalServiceAPIException) as cds_exception:
            cine_digital_service.get_screen(4)
        assert (
            str(cds_exception.value)
            == "Screen #4 not found in Cine Digital Service API for cinemaId=test_id & url=test_url"
        )


class CineDigitalServiceGetAvailableSingleSeatTest:
    @patch("pcapi.core.booking_providers.cds.CineDigitalService.get_seatmap")
    def test_should_return_seat_available(self, mocked_get_seatmap):
        seatmap = cds_serializers.SeatmapCDS(
            __root__=[
                [1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
                [1, 3, 1, 1, 1, 1, 1, 1, 0, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1],
                [0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1],
            ]
        )
        screen = cds_serializers.ScreenCDS(
            id=1,
            seatmapfronttoback=True,
            seatmaplefttoright=True,
            seatmapskipmissingseats=False,
        )

        mocked_get_seatmap.return_value = seatmap
        cine_digital_service = CineDigitalServiceAPI(cinemaid="test_id", token="token_test", apiUrl="test_url")
        best_seat = cine_digital_service.get_available_seat(1, screen)
        assert best_seat.seatRow == 5
        assert best_seat.seatCol == 6
        assert best_seat.seatNumber == "E_6"

    @patch("pcapi.core.booking_providers.cds.CineDigitalService.get_seatmap")
    def test_should_return_seat_infos_according_to_screen(self, mocked_get_seatmap):
        seatmap = cds_serializers.SeatmapCDS(
            __root__=[
                [3, 3, 3, 3, 0, 3],
                [3, 3, 3, 3, 0, 3],
                [3, 3, 3, 3, 0, 3],
                [3, 3, 3, 1, 0, 3],
                [3, 3, 3, 3, 0, 3],
            ]
        )
        screen = cds_serializers.ScreenCDS(
            id=1,
            seatmapfronttoback=False,
            seatmaplefttoright=False,
            seatmapskipmissingseats=True,
        )

        mocked_get_seatmap.return_value = seatmap
        cine_digital_service = CineDigitalServiceAPI(cinemaid="test_id", token="token_test", apiUrl="test_url")
        best_seat = cine_digital_service.get_available_seat(1, screen)
        assert best_seat.seatRow == 2
        assert best_seat.seatCol == 2
        assert best_seat.seatNumber == "B_2"

    @patch("pcapi.core.booking_providers.cds.CineDigitalService.get_seatmap")
    def test_should_return_None_if_no_seat_available(self, mocked_get_seatmap):
        seatmap = cds_serializers.SeatmapCDS(
            __root__=[
                [3, 3, 3, 3, 0, 3],
                [3, 3, 3, 3, 0, 3],
                [3, 3, 3, 3, 0, 3],
                [3, 3, 3, 3, 0, 3],
                [3, 3, 3, 3, 0, 3],
            ]
        )
        screen = cds_serializers.ScreenCDS(
            id=1,
            seatmapfronttoback=True,
            seatmaplefttoright=True,
            seatmapskipmissingseats=False,
        )

        mocked_get_seatmap.return_value = seatmap
        cine_digital_service = CineDigitalServiceAPI(cinemaid="test_id", token="token_test", apiUrl="test_url")
        best_seat = cine_digital_service.get_available_seat(1, screen)
        assert best_seat is None


class CineDigitalServiceGetAvailableDuoSeatTest:
    @patch("pcapi.core.booking_providers.cds.CineDigitalService.get_seatmap")
    def test_should_return_duo_seat_if_available(self, mocked_get_seatmap):
        seatmap = cds_serializers.SeatmapCDS(
            __root__=[
                [1, 1, 1, 1, 0, 1],
                [1, 1, 1, 3, 0, 1],
                [1, 1, 3, 3, 0, 1],
                [1, 1, 3, 1, 0, 1],
                [1, 1, 1, 1, 0, 1],
            ]
        )
        screen = cds_serializers.ScreenCDS(
            id=1,
            seatmapfronttoback=True,
            seatmaplefttoright=True,
            seatmapskipmissingseats=False,
        )

        mocked_get_seatmap.return_value = seatmap
        cine_digital_service = CineDigitalServiceAPI(cinemaid="test_id", token="token_test", apiUrl="test_url")
        duo_seats = cine_digital_service.get_available_duo_seat(1, screen)
        assert len(duo_seats) == 2
        assert duo_seats[0].seatNumber == "B_3"
        assert duo_seats[1].seatNumber == "B_2"

    @patch("pcapi.core.booking_providers.cds.CineDigitalService.get_seatmap")
    def test_should_return_empty_if_less_than_two_seats_available(self, mocked_get_seatmap):
        seatmap = cds_serializers.SeatmapCDS(
            __root__=[
                [3, 3, 3, 3, 0, 1],
                [3, 3, 3, 3, 0, 3],
                [3, 3, 3, 3, 0, 3],
                [3, 3, 3, 3, 0, 3],
                [3, 3, 3, 3, 0, 3],
            ]
        )
        screen = cds_serializers.ScreenCDS(
            id=1,
            seatmapfronttoback=True,
            seatmaplefttoright=True,
            seatmapskipmissingseats=False,
        )

        mocked_get_seatmap.return_value = seatmap
        cine_digital_service = CineDigitalServiceAPI(cinemaid="test_id", token="token_test", apiUrl="test_url")
        duo_seats = cine_digital_service.get_available_duo_seat(1, screen)
        assert len(duo_seats) == 0

    @patch("pcapi.core.booking_providers.cds.CineDigitalService.get_seatmap")
    def test_should_return_two_separate_seats_if_no_duo_available(self, mocked_get_seatmap):
        seatmap = cds_serializers.SeatmapCDS(
            __root__=[
                [1, 3, 1, 3, 0, 1],
                [3, 3, 3, 3, 0, 3],
                [1, 3, 1, 3, 0, 1],
                [3, 3, 1, 3, 0, 3],
                [3, 1, 3, 1, 0, 1],
            ]
        )
        screen = cds_serializers.ScreenCDS(
            id=1,
            seatmapfronttoback=True,
            seatmaplefttoright=True,
            seatmapskipmissingseats=False,
        )

        mocked_get_seatmap.return_value = seatmap
        cine_digital_service = CineDigitalServiceAPI(cinemaid="test_id", token="token_test", apiUrl="test_url")
        duo_seats = cine_digital_service.get_available_duo_seat(1, screen)
        assert len(duo_seats) == 2
        assert duo_seats[0].seatNumber == "C_3"
        assert duo_seats[1].seatNumber == "D_3"
