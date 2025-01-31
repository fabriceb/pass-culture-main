import csv
from datetime import date
from datetime import datetime
from enum import Enum
from io import StringIO
from typing import Optional

from pydantic import root_validator
from sqlalchemy.orm import Query

from pcapi.core.bookings.models import BookingStatus
from pcapi.core.bookings.repository import BOOKING_STATUS_LABELS
from pcapi.core.bookings.utils import convert_booking_dates_utc_to_venue_timezone
from pcapi.core.educational.models import CollectiveBookingStatus
from pcapi.core.educational.models import CollectiveBookingStatusFilter
from pcapi.core.educational.repository import CollectiveBookingNamedTuple
from pcapi.models.api_errors import ApiErrors
from pcapi.routes.serialization import BaseModel
from pcapi.serialization.utils import dehumanize_field
from pcapi.serialization.utils import to_camel
from pcapi.utils.date import format_into_timezoned_date
from pcapi.utils.date import format_into_utc_date
from pcapi.utils.human_ids import humanize


class CollectiveBookingRecapStatus(Enum):
    booked = "réservé"
    validated = "validé"
    cancelled = "annulé"
    reimbursed = "remboursé"
    confirmed = "confirmé"
    pending = "préréservé"


class ListCollectiveBookingsQueryModel(BaseModel):
    page: int = 1
    venue_id: Optional[int]
    event_date: Optional[datetime]
    booking_status_filter: Optional[CollectiveBookingStatusFilter]
    booking_period_beginning_date: Optional[date]
    booking_period_ending_date: Optional[date]

    _dehumanize_venue_id = dehumanize_field("venue_id")

    class Config:
        alias_generator = to_camel

    extra = "forbid"

    @root_validator(pre=True)
    def booking_period_or_event_date_required(cls, values):  # type: ignore [no-untyped-def] # pylint: disable=no-self-argument
        event_date = values.get("eventDate")
        booking_period_beginning_date = values.get("bookingPeriodBeginningDate")
        booking_period_ending_date = values.get("bookingPeriodEndingDate")
        if not event_date and not (booking_period_beginning_date and booking_period_ending_date):
            raise ApiErrors(
                errors={
                    "eventDate": ["Ce champ est obligatoire si aucune période n'est renseignée."],
                    "bookingPeriodEndingDate": ["Ce champ est obligatoire si la date d'évènement n'est renseignée"],
                    "bookingPeriodBeginningDate": ["Ce champ est obligatoire si la date d'évènement n'est renseignée"],
                }
            )
        return values


class BookingStatusHistoryResponseModel(BaseModel):
    status: str
    date: str


class CollectiveStockResponseModel(BaseModel):
    offer_name: str
    offer_identifier: str
    event_beginning_datetime: str
    offer_isbn: None = None
    offer_is_educational = True


class EducationalRedactorResponseModel(BaseModel):
    lastname: str
    firstname: str
    email: str
    phonenumber: Optional[str]


class CollectiveBookingResponseModel(BaseModel):
    stock: CollectiveStockResponseModel
    beneficiary: EducationalRedactorResponseModel
    booking_token: None = None
    booking_date: str
    booking_status: str
    booking_is_duo = False
    booking_amount: float
    booking_status_history: list[BookingStatusHistoryResponseModel]


class ListCollectiveBookingsResponseModel(BaseModel):
    bookings_recap: list[CollectiveBookingResponseModel]
    page: int
    pages: int
    total: int

    class Config:
        json_encoders = {datetime: format_into_utc_date}


def _get_booking_status(status: CollectiveBookingStatus, is_confirmed: bool) -> str:
    cancellation_limit_date_exists_and_past = is_confirmed
    if cancellation_limit_date_exists_and_past and status == BookingStatus.CONFIRMED:
        return BOOKING_STATUS_LABELS["confirmed"]
    return BOOKING_STATUS_LABELS[status]


def build_status_history(
    booking_status: CollectiveBookingStatus,
    booking_date: datetime,
    cancellation_date: Optional[datetime],
    cancellation_limit_date: Optional[datetime],
    payment_date: Optional[datetime],
    date_used: Optional[datetime],
    confirmation_date: Optional[datetime],
    is_confirmed: Optional[bool],
) -> list[BookingStatusHistoryResponseModel]:

    if booking_status == CollectiveBookingStatus.PENDING:
        serialized_booking_status_history = [
            _serialize_collective_booking_status_info(CollectiveBookingRecapStatus.pending, booking_date)
        ]
        return serialized_booking_status_history

    if booking_status == CollectiveBookingStatus.CANCELLED and not (confirmation_date or booking_date):
        serialized_booking_status_history = [
            _serialize_collective_booking_status_info(CollectiveBookingRecapStatus.cancelled, cancellation_date)
        ]
        return serialized_booking_status_history

    serialized_booking_status_history = [
        _serialize_collective_booking_status_info(
            CollectiveBookingRecapStatus.booked, confirmation_date or booking_date
        )
    ]
    if is_confirmed and confirmation_date is not None:
        serialized_booking_status_history.append(
            _serialize_collective_booking_status_info(CollectiveBookingRecapStatus.confirmed, cancellation_limit_date)
        )
    if date_used:
        serialized_booking_status_history.append(
            _serialize_collective_booking_status_info(CollectiveBookingRecapStatus.validated, date_used)
        )

    if cancellation_date:
        serialized_booking_status_history.append(
            _serialize_collective_booking_status_info(CollectiveBookingRecapStatus.cancelled, cancellation_date)
        )
    if payment_date:
        serialized_booking_status_history.append(
            _serialize_collective_booking_status_info(CollectiveBookingRecapStatus.reimbursed, payment_date)
        )
    return serialized_booking_status_history


def _serialize_collective_booking_status_info(
    collective_booking_status: CollectiveBookingRecapStatus, collective_booking_status_date: Optional[datetime]
) -> BookingStatusHistoryResponseModel:

    serialized_collective_booking_status_date = (
        format_into_timezoned_date(collective_booking_status_date) if collective_booking_status_date else None
    )

    return BookingStatusHistoryResponseModel(
        status=collective_booking_status.value,
        date=serialized_collective_booking_status_date,
    )


def serialize_collective_booking_stock(collective_booking: CollectiveBookingNamedTuple) -> CollectiveStockResponseModel:
    return CollectiveStockResponseModel(
        offer_name=collective_booking.offerName,
        offer_identifier=humanize(collective_booking.offerId),
        event_beginning_datetime=collective_booking.stockBeginningDatetime.isoformat(),
    )


def serialize_collective_booking_redactor(
    collective_booking: CollectiveBookingNamedTuple,
) -> EducationalRedactorResponseModel:
    return EducationalRedactorResponseModel(
        lastname=collective_booking.redactorLastname,
        firstname=collective_booking.redactorFirstname,
        email=collective_booking.redactorEmail,
        phonenumber=None,
    )


def _serialize_collective_booking_recap_status(
    collective_booking: CollectiveBookingNamedTuple,
) -> CollectiveBookingRecapStatus:
    if collective_booking.status == CollectiveBookingStatus.PENDING:
        return CollectiveBookingRecapStatus.pending
    if collective_booking.status == CollectiveBookingStatus.REIMBURSED:
        return CollectiveBookingRecapStatus.reimbursed
    if collective_booking.status == CollectiveBookingStatus.CANCELLED:
        return CollectiveBookingRecapStatus.cancelled
    if collective_booking.status == CollectiveBookingStatus.USED:
        return CollectiveBookingRecapStatus.validated
    if collective_booking.isConfirmed:
        return CollectiveBookingRecapStatus.confirmed
    return CollectiveBookingRecapStatus.booked


def serialize_collective_booking(collective_booking: CollectiveBookingNamedTuple) -> CollectiveBookingResponseModel:
    return CollectiveBookingResponseModel(
        stock=serialize_collective_booking_stock(collective_booking),
        beneficiary=serialize_collective_booking_redactor(collective_booking),
        booking_date=collective_booking.bookedAt.isoformat(),
        booking_status=_serialize_collective_booking_recap_status(collective_booking).value,
        booking_amount=collective_booking.bookingAmount,
        booking_status_history=build_status_history(
            booking_status=collective_booking.status,
            booking_date=collective_booking.bookedAt,
            cancellation_date=collective_booking.cancelledAt,
            cancellation_limit_date=collective_booking.cancellationLimitDate,
            payment_date=collective_booking.reimbursedAt,
            date_used=collective_booking.usedAt,
            confirmation_date=collective_booking.confirmationDate,
            is_confirmed=collective_booking.isConfirmed,
        ),
    )


def serialize_collective_booking_csv_report(query: Query) -> str:
    output = StringIO()
    writer = csv.writer(output, dialect=csv.excel, delimiter=";", quoting=csv.QUOTE_NONNUMERIC)
    writer.writerow(
        (
            "Lieu",
            "Nom de l'offre",
            "Date de l'évènement",
            "Nom et prénom du bénéficiaire",
            "Email du bénéficiaire",
            "Date et heure de réservation",
            "Date et heure de validation",
            "Prix de la réservation",
            "Date et heure de remboursement",
        )
    )
    for collective_booking in query.yield_per(1000):
        writer.writerow(
            (
                collective_booking.venueName,
                collective_booking.offerName,
                convert_booking_dates_utc_to_venue_timezone(
                    collective_booking.stockBeginningDatetime, collective_booking
                ),
                f"{collective_booking.lastName} {collective_booking.firstName}",
                collective_booking.email,
                convert_booking_dates_utc_to_venue_timezone(collective_booking.bookedAt, collective_booking),
                convert_booking_dates_utc_to_venue_timezone(collective_booking.usedAt, collective_booking),
                collective_booking.price,
                convert_booking_dates_utc_to_venue_timezone(collective_booking.reimbursedAt, collective_booking),
            )
        )

    return output.getvalue()
