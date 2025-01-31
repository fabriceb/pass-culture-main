from datetime import date
from enum import Enum
import logging
from typing import Optional

from pcapi.core.bookings import exceptions
from pcapi.core.bookings.models import Booking
from pcapi.core.bookings.models import BookingStatus
from pcapi.core.offers.models import Offer
from pcapi.core.offers.models import Stock
from pcapi.routes.serialization import BaseModel
from pcapi.utils.urls import booking_app_link


logger = logging.getLogger(__name__)


class GroupId(Enum):
    CANCEL_BOOKING = "Cancel_booking"
    TODAY_STOCK = "Today_stock"
    OFFER_LINK = "Offer_link"
    SOON_EXPIRING_BOOKINGS = "Soon_expiring_bookings"


class TransactionalNotificationMessage(BaseModel):
    body: str
    title: Optional[str] = None


class TransactionalNotificationData(BaseModel):
    group_id: str  # Name of the campaign, useful for analytics purpose
    user_ids: list[int]
    message: TransactionalNotificationMessage
    extra: Optional[dict] = {}


def get_bookings_cancellation_notification_data(booking_ids: list[int]) -> Optional[TransactionalNotificationData]:
    bookings = Booking.query.filter(Booking.id.in_(booking_ids))

    if not bookings:
        return None

    cancelled_object = (
        "commande" if bookings[0].stock.offer.isDigital or bookings[0].stock.offer.isThing else "réservation"
    )
    return TransactionalNotificationData(
        group_id=GroupId.CANCEL_BOOKING.value,
        user_ids=[booking.individualBooking.userId for booking in bookings],
        message=TransactionalNotificationMessage(
            title=f"{cancelled_object.capitalize()} annulée",
            body=f"""Ta {cancelled_object} "{bookings[0].stock.offer.name}" a été annulée par l'offreur.""",
        ),
    )


def get_today_stock_notification_data(stock_id: int) -> Optional[TransactionalNotificationData]:
    stock = Stock.query.filter_by(id=stock_id).one()
    query = (
        Booking.query.filter(Booking.stockId == stock_id, Booking.status != BookingStatus.CANCELLED)
        .join(Booking.individualBooking)  # exclude collective bookings
        .with_entities(Booking.userId)
        .distinct()
    )

    user_ids = [booking.userId for booking in query]
    if not user_ids:
        return None

    return TransactionalNotificationData(
        group_id=GroupId.TODAY_STOCK.value,
        user_ids=user_ids,
        message=TransactionalNotificationMessage(
            title="C'est aujourd'hui !",
            body=f"Retrouve les détails de la réservation pour {stock.offer.name} sur l’application pass Culture",
        ),
    )


def get_offer_notification_data(user_id: int, offer: Offer) -> TransactionalNotificationData:
    return TransactionalNotificationData(
        group_id=GroupId.OFFER_LINK.value,
        user_ids=[user_id],
        message=TransactionalNotificationMessage(
            title=f"Ta réservation pour {offer.name}",
            body="Pour la confirmer, clique sur le lien que tu as reçu par mail 📩",
        ),
    )


def get_soon_expiring_bookings_with_offers_notification_data(booking: Booking) -> TransactionalNotificationData:
    remaining_days = (booking.expirationDate.date() - date.today()).days  # type: ignore [union-attr]

    if remaining_days < 0:
        raise exceptions.BookingIsExpired(booking.id)

    if remaining_days > 1:
        body = f'Vite, il ne te reste plus que {remaining_days} jours pour récupérer "{booking.stock.offer.name}"'
    elif remaining_days == 1:
        body = f'Vite, il ne te reste plus qu\'un jour pour récupérer "{booking.stock.offer.name}"'
    else:
        body = f'Vite, dernier jour pour récupérer "{booking.stock.offer.name}"'

    return TransactionalNotificationData(
        group_id=GroupId.SOON_EXPIRING_BOOKINGS.value,
        user_ids=[booking.userId],
        message=TransactionalNotificationMessage(title="Tu n'as pas récupéré ta réservation", body=body),
        extra={"deeplink": booking_app_link(booking)},
    )
