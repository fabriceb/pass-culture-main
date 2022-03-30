from pcapi.connectors.cine_digital_service import get_screens
from pcapi.connectors.cine_digital_service import get_shows
import pcapi.connectors.serialization.cine_digital_service_serializers as cds_serializers
import pcapi.core.booking_providers.cds.exceptions as cds_exceptions


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
