from pcapi.connectors.cine_digital_service import build_url
from pcapi.connectors.cine_digital_service import get_resource
from pcapi.connectors.cine_digital_service import parse_json_data
from pcapi.connectors.cine_digital_service import resourceCDS
import pcapi.connectors.serialization.cine_digital_service_serializers as cds_serializers
import pcapi.core.booking_providers.cds.exceptions as cds_exceptions
from pcapi.core.booking_providers.cds.mocked_api_calls import MockedPaymentType
from pcapi.core.booking_providers.cds.mocked_api_calls import MockedScreens
from pcapi.core.booking_providers.cds.mocked_api_calls import MockedShows
from pcapi.core.booking_providers.cds.mocked_api_calls import MockedTariffs


class CineDigitalServiceAPI:
    def __init__(self, cinemaid: str, token: str, apiUrl: str):
        self.token = token
        self.apiUrl = apiUrl
        self.cinemaid = cinemaid

    def get_show(self, show_id: int) -> cds_serializers.ShowCDS:
        url = build_url(self.cinemaid, self.apiUrl, self.token, resourceCDS.SHOWS)
        data = get_resource(url, MockedShows)
        shows = parse_json_data(data, cds_serializers.ShowCDS)
        for show in shows:
            if show.id == show_id:
                return show
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Show #{show_id} not found in Cine Digital Service API for cinemaId={self.cinemaid} & url={self.apiUrl}"
        )

    def get_payment_type(self) -> cds_serializers.PaymentTypeCDS:
        url = build_url(self.cinemaid, self.apiUrl, self.token, resourceCDS.PAYMENT_TYPE)
        data = get_resource(url, MockedPaymentType)
        payment_types = parse_json_data(data, cds_serializers.PaymentTypeCDS)
        for payment_type in payment_types:
            if payment_type.short_label == "PASSCULTURE":
                return payment_type

        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Pass Culture payment type not found in Cine Digital Service API for cinemaId={self.cinemaid}"
            f" & url={self.apiUrl}"
        )

    def get_tariff(self) -> cds_serializers.TariffCDS:
        url = build_url(self.cinemaid, self.apiUrl, self.token, resourceCDS.TARIFFS)
        data = get_resource(url, MockedTariffs)
        tariffs = parse_json_data(data, cds_serializers.TariffCDS)

        for tariff in tariffs:
            if tariff.label == "Pass Culture 5€":
                return tariff
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Tariff Pass Culture not found in Cine Digital Service API for cinemaId={self.cinemaid}"
            f" & url={self.apiUrl}"
        )

    def get_screen(self, screen_id: int) -> cds_serializers.ScreenCDS:
        url = build_url(self.cinemaid, self.apiUrl, self.token, resourceCDS.SCREENS)
        data = get_resource(url, MockedScreens)
        screens = parse_json_data(data, cds_serializers.ScreenCDS)

        for screen in screens:
            if screen.id == screen_id:
                return screen
        raise cds_exceptions.CineDigitalServiceAPIException(
            f"Screen #{screen_id} not found in Cine Digital Service API for cinemaId={self.cinemaid} & url={self.apiUrl}"
        )
