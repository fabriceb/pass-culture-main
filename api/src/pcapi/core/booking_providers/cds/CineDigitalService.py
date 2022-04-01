import math

from pcapi.connectors.cine_digital_service import get_screens
from pcapi.connectors.cine_digital_service import get_seatmap
from pcapi.connectors.cine_digital_service import get_shows
import pcapi.connectors.serialization.cine_digital_service_serializers as cds_serializers
import pcapi.core.booking_providers.cds.exceptions as cds_exceptions
from pcapi.core.booking_providers.models import SeatCDS


class CineDigitalServiceAPI:
    def __init__(self, cinemaid: str, token: str, apiUrl: str):
        self.token = token
        self.apiUrl = apiUrl
        self.cinemaid = cinemaid

    def get_show(self, show_id: int) -> cds_serializers.ShowCDS:
        shows = get_shows(self.cinemaid, self.apiUrl, self.token)
        for show in shows:
            if show.id == show_id:
                return show
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Show #{show_id} not found in Cine Digital Service API for cinemaId={self.cinemaid} & url={self.apiUrl}"
        )

    def get_screen(self, screen_id: int) -> cds_serializers.ScreenCDS:
        screens = get_screens(self.cinemaid, self.apiUrl, self.token)
        for screen in screens:
            if screen.id == screen_id:
                return screen
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Screen #{screen_id} not found in Cine Digital Service API for cinemaId={self.cinemaid} & url={self.apiUrl}"
        )

    def get_available_seat(self, show_id: int, screen: cds_serializers.ScreenCDS) -> SeatCDS:
        seatmap = get_seatmap(self.cinemaid, self.apiUrl, show_id, self.token)
        available_seats_index = [
            (i, j) for i in range(0, seatmap.nb_row) for j in range(0, seatmap.nb_col) if seatmap.map[i][j] % 10 == 1
        ]
        if len(available_seats_index) == 0:
            return None
        best_seat = self.get_closest_seat_to_center((seatmap.nb_row / 2, seatmap.nb_col / 2), available_seats_index)
        return SeatCDS(best_seat, screen, seatmap)

    def get_available_duo_seat(self, show_id: int, screen: cds_serializers.ScreenCDS) -> list[SeatCDS]:

        seatmap = get_seatmap(self.cinemaid, self.apiUrl, show_id, self.token)
        seatmap_center = (math.floor(seatmap.nb_row / 2), math.floor(seatmap.nb_col / 2))

        available_seats_index = [
            (i, j) for i in range(0, seatmap.nb_row) for j in range(0, seatmap.nb_col) if seatmap.map[i][j] % 10 == 1
        ]
        if len(available_seats_index) <= 1:
            return []

        available_seats_for_duo = [
            seat
            for seat in available_seats_index
            if (seat[0], seat[1] - 1) in available_seats_index or (seat[0], seat[1] + 1) in available_seats_index
        ]

        if len(available_seats_for_duo) > 0:

            first_seat = self.get_closest_seat_to_center(seatmap_center, available_seats_for_duo)
            previous_seat = (first_seat[0], first_seat[1] - 1)
            next_seat = (first_seat[0], first_seat[1] + 1)
            if previous_seat in available_seats_index:
                second_seat = previous_seat
            elif next_seat in available_seats_index:
                second_seat = next_seat

        else:
            first_seat = self.get_closest_seat_to_center(seatmap_center, available_seats_index)
            available_seats_index.remove(first_seat)
            second_seat = self.get_closest_seat_to_center(seatmap_center, available_seats_index)

        return [
            SeatCDS(first_seat, screen, seatmap),
            SeatCDS(second_seat, screen, seatmap),
        ]

    def get_closest_seat_to_center(
        self, center: tuple[int, int], seats_index: list[tuple[int, int]]
    ) -> tuple[int, int]:
        distances_to_center = list(
            map(
                lambda seat_index: math.sqrt(pow(seat_index[0] - center[0], 2) + pow(seat_index[1] - center[1], 2)),
                seats_index,
            )
        )
        min_distance = min(distances_to_center)
        index_min_distance = distances_to_center.index(min_distance)
        return seats_index[index_min_distance]
