import datetime

from pcapi.connectors.cine_digital_service import create_transaction
from pcapi.connectors.cine_digital_service import get_shows
import pcapi.connectors.serialization.cine_digital_service_serializers as cds_serializers
import pcapi.core.booking_providers.cds.exceptions as cds_exceptions


CDS_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"


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

    def create_booking(self, show_id: int, quantity: int, amount: int) -> list[str]:
        if quantity < 0 or quantity > 2:
            raise Exception("Booking quantity should be 1 or 2")

        ticket_sale_collection = self._create_ticket_sale_dict(show_id, quantity)

        paiement = cds_serializers.PaiementCDS(
            id=-1, amount=amount * quantity, paiementtypeid=cds_serializers.IdObjectCDS(id=4)
        )  # @TODO get paiementInformation PC-14295

        create_transaction_body = cds_serializers.CreateTransactionBodyCDS(
            cinemaid=self.cinemaid,
            transactiondate=datetime.datetime.now().strftime(CDS_DATE_FORMAT),
            canceled=False,
            ticketsaleCollection=ticket_sale_collection,
            paiementCollection=[paiement],
        )

        barcodes = create_transaction(self.cinemaid, self.apiUrl, self.token, create_transaction_body)

        return barcodes

    def _create_ticket_sale_dict(self, show_id: int, quantity: int) -> list[cds_serializers.TicketSaleCDS]:
        ticket_sale_list = []
        for i in range(1, quantity + 1):
            ticket_sale = cds_serializers.TicketSaleCDS(
                id=i * -1,
                cinemaid=self.cinemaid,
                operationdate=datetime.datetime.now().strftime(CDS_DATE_FORMAT),
                canceled=False,
                seatcol=1,  # TODO(@yacine) get seating PC-14017
                seatrow=1,
                seatnumber="A_1",
                tariffid=cds_serializers.IdObjectCDS(id=32),  # TODO(@yacine) get pass culture tariff
                showid=cds_serializers.IdObjectCDS(id=show_id),
                disabledperson=False,
            )
            ticket_sale_list.append(ticket_sale)

        return ticket_sale_list
