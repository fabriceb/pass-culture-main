import copy
import datetime
import logging
from typing import List
from typing import Optional
from typing import Union

from psycopg2.errorcodes import CHECK_VIOLATION
from psycopg2.errorcodes import UNIQUE_VIOLATION
from pydantic import ValidationError
import sqlalchemy.exc as sqla_exc
import sqlalchemy.orm as sqla_orm
import yaml
from yaml.scanner import ScannerError

from pcapi import settings
from pcapi.connectors.api_adage import AdageException
from pcapi.connectors.thumb_storage import create_thumb
from pcapi.connectors.thumb_storage import remove_thumb
from pcapi.core import search
from pcapi.core.bookings.api import cancel_bookings_from_stock_by_offerer
from pcapi.core.bookings.api import cancel_collective_booking_from_stock_by_offerer
from pcapi.core.bookings.api import mark_as_unused
from pcapi.core.bookings.api import update_cancellation_limit_dates
from pcapi.core.bookings.models import Booking
from pcapi.core.bookings.models import BookingStatus
import pcapi.core.bookings.repository as bookings_repository
from pcapi.core.categories import subcategories
from pcapi.core.categories.conf import can_create_from_isbn
from pcapi.core.educational import api as educational_api
from pcapi.core.educational import exceptions as educational_exceptions
from pcapi.core.educational import models as educational_models
import pcapi.core.educational.adage_backends as adage_client
from pcapi.core.educational.models import ADAGE_STUDENT_LEVEL_MAPPING
from pcapi.core.educational.models import CollectiveOffer
from pcapi.core.educational.models import CollectiveOfferTemplate
from pcapi.core.educational.utils import compute_educational_booking_cancellation_limit_date
from pcapi.core.mails.transactional.bookings.booking_cancellation_by_pro_to_beneficiary import (
    send_booking_cancellation_by_pro_to_beneficiary_email,
)
from pcapi.core.mails.transactional.bookings.booking_cancellation_confirmation_by_pro import (
    send_booking_cancellation_confirmation_by_pro_email,
)
from pcapi.core.mails.transactional.bookings.booking_postponed_by_pro_to_beneficiary import (
    send_batch_booking_postponement_email_to_users,
)
from pcapi.core.mails.transactional.pro.event_offer_postponed_confirmation_to_pro import (
    send_event_offer_postponement_confirmation_email_to_pro,
)
from pcapi.core.mails.transactional.pro.first_venue_approved_offer_to_pro import (
    send_first_venue_approved_offer_email_to_pro,
)
from pcapi.core.mails.transactional.users.reported_offer_by_user import send_email_reported_offer_by_user
from pcapi.core.offerers import api as offerers_api
from pcapi.core.offerers.models import Venue
from pcapi.core.offers import exceptions as offers_exceptions
from pcapi.core.offers import validation
from pcapi.core.offers.exceptions import OfferAlreadyReportedError
from pcapi.core.offers.exceptions import ReportMalformed
from pcapi.core.offers.exceptions import WrongFormatInFraudConfigurationFile
from pcapi.core.offers.models import Offer
from pcapi.core.offers.models import OfferReport
from pcapi.core.offers.models import OfferValidationConfig
from pcapi.core.offers.models import OfferValidationStatus
from pcapi.core.offers.models import Stock
from pcapi.core.offers.offer_validation import compute_offer_validation_score
from pcapi.core.offers.offer_validation import parse_offer_validation_config
import pcapi.core.offers.repository as offers_repository
from pcapi.core.offers.utils import as_utc_without_timezone
from pcapi.core.offers.validation import KEY_VALIDATION_CONFIG
from pcapi.core.offers.validation import check_offer_is_eligible_for_educational
from pcapi.core.offers.validation import check_offer_subcategory_is_valid
from pcapi.core.offers.validation import check_offer_withdrawal
from pcapi.core.offers.validation import check_shadow_stock_is_editable
from pcapi.core.offers.validation import check_validation_config_parameters
from pcapi.core.payments import conf as deposit_conf
from pcapi.core.users.external import update_external_pro
from pcapi.core.users.models import ExpenseDomain
from pcapi.core.users.models import User
from pcapi.domain import admin_emails
from pcapi.domain.pro_offers.offers_recap import OffersRecap
from pcapi.models import db
from pcapi.models.api_errors import ApiErrors
from pcapi.models.criterion import Criterion
from pcapi.models.feature import FeatureToggle
from pcapi.models.offer_criterion import OfferCriterion
from pcapi.models.offer_mixin import OfferValidationType
from pcapi.models.product import Product
from pcapi.repository import offer_queries
from pcapi.repository import repository
from pcapi.repository import transaction
from pcapi.routes.adage.v1.serialization.prebooking import serialize_collective_booking
from pcapi.routes.adage.v1.serialization.prebooking import serialize_educational_booking
from pcapi.routes.serialization.offers_serialize import CompletedEducationalOfferModel
from pcapi.routes.serialization.offers_serialize import EducationalOfferShadowStockBodyModel
from pcapi.routes.serialization.offers_serialize import PostEducationalOfferBodyModel
from pcapi.routes.serialization.offers_serialize import PostOfferBodyModel
from pcapi.routes.serialization.stock_serialize import EducationalStockCreationBodyModel
from pcapi.routes.serialization.stock_serialize import StockCreationBodyModel
from pcapi.routes.serialization.stock_serialize import StockEditionBodyModel
from pcapi.utils.human_ids import dehumanize
from pcapi.utils.rest import check_user_has_access_to_offerer
from pcapi.utils.rest import load_or_raise_error
from pcapi.workers.push_notification_job import send_cancel_booking_notification

from .exceptions import ThumbnailStorageError
from .models import ActivationCode
from .models import Mediation
from .models import WithdrawalTypeEnum


logger = logging.getLogger(__name__)


OFFERS_RECAP_LIMIT = 501
UNCHANGED = object()


def list_offers_for_pro_user(
    user_id: int,
    user_is_admin: bool,
    category_id: Optional[str],
    offerer_id: Optional[int],
    venue_id: Optional[int] = None,
    name_keywords_or_isbn: Optional[str] = None,
    status: Optional[str] = None,
    creation_mode: Optional[str] = None,
    period_beginning_date: Optional[str] = None,
    period_ending_date: Optional[str] = None,
) -> OffersRecap:
    return offers_repository.get_capped_offers_for_filters(
        user_id=user_id,
        user_is_admin=user_is_admin,
        offers_limit=OFFERS_RECAP_LIMIT,
        offerer_id=offerer_id,
        status=status,
        venue_id=venue_id,
        category_id=category_id,
        name_keywords_or_isbn=name_keywords_or_isbn,
        creation_mode=creation_mode,
        period_beginning_date=period_beginning_date,
        period_ending_date=period_ending_date,
    )


def create_educational_offer(offer_data: PostEducationalOfferBodyModel, user: User) -> Offer:
    offerers_api.can_offerer_create_educational_offer(dehumanize(offer_data.offerer_id))  # type: ignore [arg-type]
    completed_data = CompletedEducationalOfferModel(**offer_data.dict(by_alias=True))
    offer = create_offer(completed_data, user)
    create_collective_offer(offer_data, user, offer.id)
    return offer


def create_collective_offer(
    offer_data: PostEducationalOfferBodyModel,
    user: User,
    offer_id: int,
) -> None:
    offerers_api.can_offerer_create_educational_offer(dehumanize(offer_data.offerer_id))  # type: ignore [arg-type]
    venue = load_or_raise_error(Venue, offer_data.venue_id)
    check_user_has_access_to_offerer(user, offerer_id=venue.managingOffererId)  # type: ignore [attr-defined]
    _check_offer_data_is_valid(offer_data, True)  # type: ignore [arg-type]
    collective_offer = educational_models.CollectiveOffer(
        venueId=venue.id,  # type: ignore [attr-defined]
        name=offer_data.name,
        offerId=offer_id,
        bookingEmail=offer_data.booking_email,
        description=offer_data.description,
        durationMinutes=offer_data.duration_minutes,
        subcategoryId=offer_data.subcategory_id,
        students=offer_data.extra_data.students,
        contactEmail=offer_data.extra_data.contact_email,
        contactPhone=offer_data.extra_data.contact_phone,
        offerVenue=offer_data.extra_data.offer_venue.dict(),
        validation=OfferValidationStatus.DRAFT,
        audioDisabilityCompliant=offer_data.audio_disability_compliant,
        mentalDisabilityCompliant=offer_data.mental_disability_compliant,
        motorDisabilityCompliant=offer_data.motor_disability_compliant,
        visualDisabilityCompliant=offer_data.visual_disability_compliant,
    )
    db.session.add(collective_offer)
    db.session.commit()
    logger.info(
        "Collective offer template has been created",
        extra={"collectiveOfferTemplate": collective_offer.id, "offerId": offer_id},
    )


def create_offer(
    offer_data: Union[PostOfferBodyModel, CompletedEducationalOfferModel],
    user: User,
) -> Offer:
    subcategory = subcategories.ALL_SUBCATEGORIES_DICT.get(offer_data.subcategory_id)  # type: ignore [arg-type]
    venue = load_or_raise_error(Venue, offer_data.venue_id)
    check_user_has_access_to_offerer(user, offerer_id=venue.managingOffererId)  # type: ignore [attr-defined]
    _check_offer_data_is_valid(offer_data, offer_data.is_educational)  # type: ignore [arg-type]
    if _is_able_to_create_book_offer_from_isbn(subcategory):  # type: ignore [arg-type]
        offer = _initialize_book_offer_from_template(offer_data)
    else:
        offer = _initialize_offer_with_new_data(offer_data, subcategory, venue)  # type: ignore [arg-type]

    _complete_common_offer_fields(offer, offer_data, venue)

    repository.save(offer)

    logger.info(  # type: ignore [call-arg]
        "Offer has been created",
        extra={"offer_id": offer.id, "venue_id": venue.id, "product_id": offer.productId},  # type: ignore [attr-defined]
        technical_message_id="offer.created",
    )

    update_external_pro(venue.bookingEmail)  # type: ignore [attr-defined]

    return offer


def _is_able_to_create_book_offer_from_isbn(subcategory: subcategories.Subcategory) -> bool:
    return FeatureToggle.ENABLE_ISBN_REQUIRED_IN_LIVRE_EDITION_OFFER_CREATION.is_active() and can_create_from_isbn(
        subcategory_id=subcategory.id
    )


def _initialize_book_offer_from_template(
    offer_data: Union[PostOfferBodyModel, CompletedEducationalOfferModel]
) -> Offer:
    product = _load_product_by_isbn_and_check_is_gcu_compatible_or_raise_error(offer_data.extra_data["isbn"])  # type: ignore [index]
    extra_data = product.extraData
    extra_data.update(offer_data.extra_data)  # type: ignore [union-attr]
    offer = Offer(
        product=product,
        subcategoryId=product.subcategoryId,
        name=offer_data.name,
        description=offer_data.description if offer_data.description else product.description,
        url=offer_data.url if offer_data.url else product.url,  # type: ignore [union-attr]
        mediaUrls=offer_data.url if offer_data.url else product.url,  # type: ignore [union-attr]
        conditions=offer_data.conditions if offer_data.conditions else product.conditions,  # type: ignore [union-attr]
        ageMin=offer_data.age_min if offer_data.age_min else product.ageMin,  # type: ignore [union-attr]
        ageMax=offer_data.age_max if offer_data.age_max else product.ageMax,  # type: ignore [union-attr]
        isNational=offer_data.is_national if offer_data.is_national else product.isNational,  # type: ignore [union-attr]
        extraData=extra_data,
    )
    return offer


def _initialize_offer_with_new_data(
    offer_data: Union[PostOfferBodyModel, CompletedEducationalOfferModel],
    subcategory: subcategories.Subcategory,
    venue: Venue,
) -> Offer:
    data = offer_data.dict(by_alias=True)
    product = Product()
    if data.get("url"):
        data["isNational"] = True
    product.populate_from_dict(data)
    offer = Offer()
    offer.populate_from_dict(data)
    offer.product = product
    offer.subcategoryId = subcategory.id if subcategory else None  # type: ignore [assignment]
    offer.product.owningOfferer = venue.managingOfferer
    return offer


def _complete_common_offer_fields(
    offer: Offer,
    offer_data: Union[PostOfferBodyModel, CompletedEducationalOfferModel],
    venue: Venue,
) -> None:
    offer.venue = venue
    offer.bookingEmail = offer_data.booking_email
    offer.externalTicketOfficeUrl = offer_data.external_ticket_office_url
    offer.audioDisabilityCompliant = offer_data.audio_disability_compliant
    offer.mentalDisabilityCompliant = offer_data.mental_disability_compliant
    offer.motorDisabilityCompliant = offer_data.motor_disability_compliant
    offer.visualDisabilityCompliant = offer_data.visual_disability_compliant
    offer.validation = OfferValidationStatus.DRAFT  # type: ignore [assignment]
    offer.isEducational = offer_data.is_educational  # type: ignore [assignment]


def _check_offer_data_is_valid(
    offer_data: Union[PostOfferBodyModel, CompletedEducationalOfferModel],
    offer_is_educational: bool,
) -> None:
    check_offer_subcategory_is_valid(offer_data.subcategory_id)
    check_offer_is_eligible_for_educational(offer_data.subcategory_id, offer_is_educational)  # type: ignore [arg-type]


def update_offer(
    offer: Offer,
    bookingEmail: str = UNCHANGED,  # type: ignore [assignment]
    description: str = UNCHANGED,  # type: ignore [assignment]
    isNational: bool = UNCHANGED,  # type: ignore [assignment]
    name: str = UNCHANGED,  # type: ignore [assignment]
    extraData: dict = UNCHANGED,  # type: ignore [assignment]
    externalTicketOfficeUrl: str = UNCHANGED,  # type: ignore [assignment]
    url: str = UNCHANGED,  # type: ignore [assignment]
    withdrawalDetails: str = UNCHANGED,  # type: ignore [assignment]
    withdrawalType: WithdrawalTypeEnum = UNCHANGED,  # type: ignore [assignment]
    withdrawalDelay: int = UNCHANGED,  # type: ignore [assignment]
    isActive: bool = UNCHANGED,  # type: ignore [assignment]
    isDuo: bool = UNCHANGED,  # type: ignore [assignment]
    durationMinutes: int = UNCHANGED,  # type: ignore [assignment]
    mediaUrls: list[str] = UNCHANGED,  # type: ignore [assignment]
    ageMin: int = UNCHANGED,  # type: ignore [assignment]
    ageMax: int = UNCHANGED,  # type: ignore [assignment]
    conditions: str = UNCHANGED,  # type: ignore [assignment]
    venueId: str = UNCHANGED,  # type: ignore [assignment]
    productId: str = UNCHANGED,  # type: ignore [assignment]
    audioDisabilityCompliant: bool = UNCHANGED,  # type: ignore [assignment]
    mentalDisabilityCompliant: bool = UNCHANGED,  # type: ignore [assignment]
    motorDisabilityCompliant: bool = UNCHANGED,  # type: ignore [assignment]
    visualDisabilityCompliant: bool = UNCHANGED,  # type: ignore [assignment]
) -> Offer:
    validation.check_validation_status(offer)
    # fmt: off
    modifications = {
        field: new_value
        for field, new_value in locals().items()
        if field != 'offer'
        and new_value is not UNCHANGED  # has the user provided a value for this field
        and getattr(offer, field) != new_value  # is the value different from what we have on database?
    }
    # fmt: on
    if not modifications:
        return offer

    if (UNCHANGED, UNCHANGED) != (withdrawalType, withdrawalDelay):
        try:
            changed_withdrawalType = withdrawalType if withdrawalType != UNCHANGED else offer.withdrawalType
            changed_withdrawalDelay = withdrawalDelay if withdrawalDelay != UNCHANGED else offer.withdrawalDelay
            check_offer_withdrawal(changed_withdrawalType, changed_withdrawalDelay, offer.subcategoryId)  # type: ignore [arg-type]
        except offers_exceptions.OfferCreationBaseException as error:
            raise ApiErrors(
                error.errors,
                status_code=400,
            )

    if offer.isFromProvider:
        validation.check_update_only_allowed_fields_for_offer_from_provider(set(modifications), offer.lastProvider)

    offer.populate_from_dict(modifications)
    if offer.product.owningOfferer and offer.product.owningOfferer == offer.venue.managingOfferer:
        offer.product.populate_from_dict(modifications)
        product_has_been_updated = True
    else:
        product_has_been_updated = False

    if offer.isFromAllocine:
        offer.fieldsUpdated = list(set(offer.fieldsUpdated) | set(modifications))

    repository.save(offer)

    logger.info("Offer has been updated", extra={"offer_id": offer.id}, technical_message_id="offer.updated")  # type: ignore [call-arg]
    if product_has_been_updated:
        repository.save(offer.product)
        logger.info("Product has been updated", extra={"product": offer.product.id})

    search.async_index_offer_ids([offer.id])

    return offer


def update_educational_offer(  # type: ignore [return]
    offer: Offer,
    new_values: dict,
) -> Offer:
    validation.check_validation_status(offer)
    # This variable is meant for Adage mailing
    updated_fields = []
    for key, value in new_values.items():
        if key == "extraData":
            extra_data = copy.deepcopy(offer.extraData)

            for extra_data_key, extra_data_value in value.items():
                # We denormalize extra_data for Adage mailing
                updated_fields.append(extra_data_key)
                extra_data[extra_data_key] = extra_data_value  # type: ignore [index]

            offer.extraData = extra_data
            continue

        updated_fields.append(key)

        if key == "subcategoryId":
            validation.check_offer_is_eligible_for_educational(value.name, True)
            offer.subcategoryId = value.name
            continue

        setattr(offer, key, value)

    repository.save(offer)

    search.async_index_offer_ids([offer.id])

    educational_api.notify_educational_redactor_on_educational_offer_or_stock_edit(
        offer.id,  # type: ignore [arg-type]
        updated_fields,
    )


def update_collective_offer(
    offer_id: str,
    is_offer_showcase: bool,
    new_values: dict,
) -> None:
    offer_to_update = (
        educational_models.CollectiveOfferTemplate.query.filter(
            educational_models.CollectiveOfferTemplate.offerId == offer_id
        ).first()
        if is_offer_showcase
        else educational_models.CollectiveOffer.query.filter(
            educational_models.CollectiveOffer.offerId == offer_id
        ).first()
    )

    if offer_to_update is None:
        # FIXME (MathildeDuboille - 2022-03-07): raise an error once all data has been migrated (PC-13427)
        return

    validation.check_validation_status(offer_to_update)
    # This variable is meant for Adage mailing
    updated_fields = []
    for key, value in new_values.items():
        updated_fields.append(key)

        # FIXME (MathildeDuboille - 2022-03-07): remove this "if" once ENABLE_NEW_COLLECTIVE_MODEL FF is enabled on production
        if key == "extraData":
            for extra_data_key, extra_data_value in value.items():
                # We denormalize extra_data for Adage mailing
                updated_fields.append(extra_data_key)

                if extra_data_key == "students":
                    students = [ADAGE_STUDENT_LEVEL_MAPPING[student] for student in extra_data_value]
                    setattr(offer_to_update, extra_data_key, students)
                    continue

                setattr(offer_to_update, extra_data_key, extra_data_value)
            continue

        if key == "subcategoryId":
            validation.check_offer_is_eligible_for_educational(value.name, True)
            offer_to_update.subcategoryId = value.name
            continue

        setattr(offer_to_update, key, value)

    db.session.add(offer_to_update)
    db.session.commit()

    if is_offer_showcase:
        search.async_index_collective_offer_template_ids([offer_to_update.id])
    else:
        search.async_index_collective_offer_ids([offer_to_update.id])

    if FeatureToggle.ENABLE_NEW_COLLECTIVE_MODEL.is_active():
        educational_api.notify_educational_redactor_on_collective_offer_or_stock_edit(
            offer_to_update.id,
            updated_fields,
        )


def batch_update_offers(query, update_fields):  # type: ignore [no-untyped-def]
    raw_results = (
        query.filter(Offer.validation == OfferValidationStatus.APPROVED).with_entities(Offer.id, Offer.venueId).all()
    )
    offer_ids, venue_ids = [], []
    if raw_results:
        offer_ids, venue_ids = zip(*raw_results)
    venue_ids = sorted(set(venue_ids))
    logger.info(
        "Batch update of offers",
        extra={"updated_fields": update_fields, "nb_offers": len(offer_ids), "venue_ids": venue_ids},
    )

    number_of_offers_to_update = len(offer_ids)
    batch_size = 1000
    for current_start_index in range(0, number_of_offers_to_update, batch_size):
        offer_ids_batch = offer_ids[
            current_start_index : min(current_start_index + batch_size, number_of_offers_to_update)
        ]

        query_to_update = Offer.query.filter(Offer.id.in_(offer_ids_batch))
        query_to_update.update(update_fields, synchronize_session=False)
        db.session.commit()

        search.async_index_offer_ids(offer_ids_batch)


def batch_update_collective_offers(query, update_fields):  # type: ignore [no-untyped-def]
    collective_offer_ids_tuples = query.filter(
        CollectiveOffer.validation == OfferValidationStatus.APPROVED
    ).with_entities(CollectiveOffer.id)

    collective_offer_ids = [offer_id for offer_id, in collective_offer_ids_tuples]
    number_of_collective_offers_to_update = len(collective_offer_ids)
    batch_size = 1000

    for current_start_index in range(0, number_of_collective_offers_to_update, batch_size):
        collective_offer_ids_batch = collective_offer_ids[
            current_start_index : min(current_start_index + batch_size, number_of_collective_offers_to_update)
        ]

        query_to_update = CollectiveOffer.query.filter(CollectiveOffer.id.in_(collective_offer_ids_batch))
        query_to_update.update(update_fields, synchronize_session=False)
        db.session.commit()

        search.async_index_collective_offer_ids(collective_offer_ids_batch)


def batch_update_collective_offers_template(query, update_fields):  # type: ignore [no-untyped-def]
    collective_offer_ids_tuples = query.filter(
        CollectiveOffer.validation == OfferValidationStatus.APPROVED
    ).with_entities(CollectiveOfferTemplate.id)

    collective_offer_template_ids = [offer_id for offer_id, in collective_offer_ids_tuples]
    number_of_collective_offers_template_to_update = len(collective_offer_template_ids)
    batch_size = 1000

    for current_start_index in range(0, number_of_collective_offers_template_to_update, batch_size):
        collective_offer_template_ids_batch = collective_offer_template_ids[
            current_start_index : min(current_start_index + batch_size, number_of_collective_offers_template_to_update)
        ]

        query_to_update = CollectiveOfferTemplate.query.filter(
            CollectiveOfferTemplate.id.in_(collective_offer_template_ids_batch)
        )
        query_to_update.update(update_fields, synchronize_session=False)
        db.session.commit()

        search.async_index_collective_offer_template_ids(collective_offer_template_ids_batch)


def _create_stock(
    offer: Offer,
    price: float,
    quantity: int = None,
    beginning: datetime.datetime = None,
    booking_limit_datetime: datetime.datetime = None,
) -> Stock:
    validation.check_required_dates_for_stock(offer, beginning, booking_limit_datetime)
    validation.check_stock_can_be_created_for_offer(offer)
    validation.check_stock_price(price, offer)
    validation.check_stock_quantity(quantity)

    return Stock(
        offer=offer,
        price=price,
        quantity=quantity,
        beginningDatetime=beginning,
        bookingLimitDatetime=booking_limit_datetime,
    )


def _edit_stock(
    stock: Stock,
    price: float,
    quantity: int,
    beginning: datetime.datetime,
    booking_limit_datetime: datetime.datetime,
) -> Stock:
    # FIXME (dbaty, 2020-11-25): We need this ugly workaround because
    # the frontend sends us datetimes like "2020-12-03T14:00:00Z"
    # (note the "Z" suffix). Pydantic deserializes it as a datetime
    # *with* a timezone. However, datetimes are stored in the database
    # as UTC datetimes *without* any timezone. Thus, we wrongly detect
    # a change for the "beginningDatetime" field for Allocine stocks:
    # because we do not allow it to be changed, we raise an error when
    # we should not.

    if beginning:
        beginning = as_utc_without_timezone(beginning)
    if booking_limit_datetime:
        booking_limit_datetime = as_utc_without_timezone(booking_limit_datetime)

    validation.check_stock_is_updatable(stock)
    validation.check_required_dates_for_stock(stock.offer, beginning, booking_limit_datetime)
    validation.check_stock_price(price, stock.offer)
    validation.check_stock_quantity(quantity, stock.dnBookedQuantity)
    validation.check_activation_codes_expiration_datetime_on_stock_edition(
        stock.activationCodes,
        booking_limit_datetime,
    )

    updates = {
        "price": price,
        "quantity": quantity,
        "beginningDatetime": beginning,
        "bookingLimitDatetime": booking_limit_datetime,
    }

    if stock.offer.isFromAllocine:
        # fmt: off
        updated_fields = {
            attr
            for attr, new_value in updates.items()
            if new_value != getattr(stock, attr)
        }
        # fmt: on
        validation.check_update_only_allowed_stock_fields_for_allocine_offer(updated_fields)
        stock.fieldsUpdated = list(set(stock.fieldsUpdated) | updated_fields)

    for model_attr, value in updates.items():
        setattr(stock, model_attr, value)

    return stock


def _notify_pro_upon_stock_edit_for_event_offer(stock: Stock, bookings: List[Booking]):  # type: ignore [no-untyped-def]
    if stock.offer.isEvent:
        if not send_event_offer_postponement_confirmation_email_to_pro(stock, len(bookings)):
            logger.warning(
                "Could not notify pro about update of stock concerning an event offer",
                extra={"stock": stock.id},
            )


def _notify_beneficiaries_upon_stock_edit(stock: Stock, bookings: List[Booking]):  # type: ignore [no-untyped-def]
    if bookings:
        bookings = update_cancellation_limit_dates(bookings, stock.beginningDatetime)  # type: ignore [arg-type]
        date_in_two_days = datetime.datetime.utcnow() + datetime.timedelta(days=2)
        check_event_is_in_more_than_48_hours = stock.beginningDatetime > date_in_two_days  # type: ignore [operator]
        if check_event_is_in_more_than_48_hours:
            bookings = _invalidate_bookings(bookings)
        if not send_batch_booking_postponement_email_to_users(bookings):
            logger.warning(
                "Could not notify beneficiaries about update of stock",
                extra={"stock": stock.id},
            )


def upsert_stocks(
    offer_id: int, stock_data_list: list[Union[StockCreationBodyModel, StockEditionBodyModel]], user: User
) -> list[Stock]:
    activation_codes = []
    stocks = []
    edited_stocks = []
    edited_stocks_previous_beginnings = {}

    offer = offer_queries.get_offer_by_id(offer_id)

    for stock_data in stock_data_list:
        if isinstance(stock_data, StockEditionBodyModel):
            stock = (
                Stock.queryNotSoftDeleted()
                .filter_by(id=stock_data.id)
                .options(sqla_orm.joinedload(Stock.activationCodes))
                .first_or_404()
            )
            if stock.offerId != offer_id:
                errors = ApiErrors()
                errors.add_error(
                    "global", "Vous n'avez pas les droits d'accès suffisant pour accéder à cette information."
                )
                errors.status_code = 403
                raise errors
            edited_stocks_previous_beginnings[stock.id] = stock.beginningDatetime
            edited_stock = _edit_stock(
                stock,
                price=stock_data.price,
                quantity=stock_data.quantity,  # type: ignore [arg-type]
                beginning=stock_data.beginning_datetime,  # type: ignore [arg-type]
                booking_limit_datetime=stock_data.booking_limit_datetime,  # type: ignore [arg-type]
            )
            edited_stocks.append(edited_stock)
            stocks.append(edited_stock)
        else:
            activation_codes_exist = stock_data.activation_codes is not None and len(stock_data.activation_codes) > 0  # type: ignore[arg-type]

            if activation_codes_exist:
                validation.check_offer_is_digital(offer)
                validation.check_activation_codes_expiration_datetime(
                    stock_data.activation_codes_expiration_datetime,
                    stock_data.booking_limit_datetime,
                )

            quantity = len(stock_data.activation_codes) if activation_codes_exist else stock_data.quantity  # type: ignore[arg-type]

            created_stock = _create_stock(
                offer=offer,
                price=stock_data.price,
                quantity=quantity,
                beginning=stock_data.beginning_datetime,
                booking_limit_datetime=stock_data.booking_limit_datetime,
            )

            if activation_codes_exist:
                for activation_code in stock_data.activation_codes:  # type: ignore[union-attr]
                    activation_codes.append(
                        ActivationCode(
                            code=activation_code,
                            expirationDate=stock_data.activation_codes_expiration_datetime,
                            stock=created_stock,
                        )
                    )

            stocks.append(created_stock)

    repository.save(*stocks, *activation_codes)
    logger.info("Stock has been created or updated", extra={"offer": offer_id})

    if offer.validation == OfferValidationStatus.DRAFT:
        _update_offer_fraud_information(offer, user)

    for stock in edited_stocks:
        previous_beginning = edited_stocks_previous_beginnings[stock.id]
        if stock.beginningDatetime != previous_beginning and not stock.offer.isEducational:
            bookings = bookings_repository.find_not_cancelled_bookings_by_stock(stock)
            _notify_pro_upon_stock_edit_for_event_offer(stock, bookings)
            _notify_beneficiaries_upon_stock_edit(stock, bookings)
    search.async_index_offer_ids([offer.id])

    return stocks


def _update_offer_fraud_information(
    offer: Union[educational_models.CollectiveOffer, Offer], user: User, *, silent: bool = False
) -> None:
    venue_already_has_validated_offer = _venue_already_has_validated_offer(offer)

    offer.validation = set_offer_status_based_on_fraud_criteria(offer)  # type: ignore [assignment]
    offer.author = user
    offer.lastValidationDate = datetime.datetime.utcnow()
    offer.lastValidationType = OfferValidationType.AUTO  # type: ignore [assignment]

    if offer.validation in (OfferValidationStatus.PENDING, OfferValidationStatus.REJECTED):
        offer.isActive = False
    repository.save(offer)
    if offer.validation == OfferValidationStatus.APPROVED and not silent:
        admin_emails.send_offer_creation_notification_to_administration(offer)

    if (
        offer.validation == OfferValidationStatus.APPROVED
        and not offer.isEducational
        and not venue_already_has_validated_offer
    ):
        if not send_first_venue_approved_offer_email_to_pro(offer):
            logger.warning("Could not send first venue approved offer email", extra={"offer_id": offer.id})


def _venue_already_has_validated_offer(offer: Offer) -> bool:
    return (
        Offer.query.filter(
            Offer.venueId == offer.venueId,
            Offer.validation == OfferValidationStatus.APPROVED,
            Offer.lastValidationDate.isnot(None),
        ).first()
        is not None
    )


def create_educational_stock(stock_data: EducationalStockCreationBodyModel, user: User) -> Stock:
    offer_id = stock_data.offer_id
    beginning = stock_data.beginning_datetime
    booking_limit_datetime = stock_data.booking_limit_datetime
    total_price = stock_data.total_price
    number_of_tickets = stock_data.number_of_tickets
    educational_price_detail = stock_data.educational_price_detail

    offer = Offer.query.filter_by(id=offer_id).options(sqla_orm.joinedload(Offer.stocks)).one()
    if len(offer.activeStocks) > 0:
        raise educational_exceptions.EducationalStockAlreadyExists()

    if not offer.isEducational:
        raise educational_exceptions.OfferIsNotEducational(offer_id)
    validation.check_validation_status(offer)
    if booking_limit_datetime is None:
        booking_limit_datetime = beginning

    stock = Stock(
        offer=offer,
        beginningDatetime=beginning,
        bookingLimitDatetime=booking_limit_datetime,
        price=total_price,
        numberOfTickets=number_of_tickets,
        educationalPriceDetail=educational_price_detail,
        quantity=1,
    )
    repository.save(stock)
    logger.info("Educational stock has been created", extra={"offer": offer_id})

    if offer.validation == OfferValidationStatus.DRAFT:
        _update_offer_fraud_information(offer, user, silent=FeatureToggle.ENABLE_NEW_COLLECTIVE_MODEL.is_active())

    search.async_index_offer_ids([offer.id])

    return stock


def edit_educational_stock(stock: Stock, stock_data: dict) -> Stock:
    beginning = stock_data.get("beginningDatetime")
    booking_limit_datetime = stock_data.get("bookingLimitDatetime")

    if not stock.offer.isEducational:
        raise educational_exceptions.OfferIsNotEducational(stock.offerId)

    beginning = as_utc_without_timezone(beginning) if beginning else None
    booking_limit_datetime = as_utc_without_timezone(booking_limit_datetime) if booking_limit_datetime else None

    updatable_fields = _extract_updatable_fields_from_stock_data(stock, stock_data, beginning, booking_limit_datetime)  # type: ignore [arg-type]

    validation.check_booking_limit_datetime(stock, beginning, booking_limit_datetime)

    educational_stock_unique_booking = bookings_repository.find_unique_eac_booking_if_any(stock.id)
    if educational_stock_unique_booking:
        validation.check_stock_booking_status(educational_stock_unique_booking)  # type: ignore [arg-type]

        educational_stock_unique_booking.educationalBooking.confirmationLimitDate = updatable_fields[  # type: ignore [attr-defined]
            "bookingLimitDatetime"
        ]
        db.session.add(educational_stock_unique_booking.educationalBooking)  # type: ignore [attr-defined]

        if beginning:
            _update_educational_booking_cancellation_limit_date(educational_stock_unique_booking, beginning)  # type: ignore [arg-type]
            db.session.add(educational_stock_unique_booking)

        if stock_data.get("price"):
            educational_stock_unique_booking.amount = stock_data.get("price")  # type: ignore [attr-defined]
            db.session.add(educational_stock_unique_booking)

    validation.check_educational_stock_is_editable(stock)

    with transaction():
        stock = offers_repository.get_and_lock_stock(stock.id)
        for attribute, new_value in updatable_fields.items():
            if new_value is not None and getattr(stock, attribute) != new_value:
                setattr(stock, attribute, new_value)
        db.session.add(stock)
        db.session.commit()

    logger.info("Stock has been updated", extra={"stock": stock.id})

    search.async_index_offer_ids([stock.offerId])

    if not FeatureToggle.ENABLE_NEW_COLLECTIVE_MODEL.is_active():
        educational_api.notify_educational_redactor_on_educational_offer_or_stock_edit(
            stock.offerId,  # type: ignore [arg-type]
            list(stock_data.keys()),
        )

    db.session.refresh(stock)
    return stock


def _extract_updatable_fields_from_stock_data(
    stock: Stock, stock_data: dict, beginning: datetime.datetime, booking_limit_datetime: datetime.datetime
) -> dict:
    # if booking_limit_datetime is provided but null, set it to default value which is event datetime
    if "bookingLimitDatetime" in stock_data.keys() and booking_limit_datetime is None:
        booking_limit_datetime = beginning if beginning else stock.beginningDatetime

    if "bookingLimitDatetime" not in stock_data.keys():
        booking_limit_datetime = stock.bookingLimitDatetime  # type: ignore [assignment]

    updatable_fields = {
        "beginningDatetime": beginning,
        "bookingLimitDatetime": booking_limit_datetime,
        "price": stock_data.get("price"),
        "numberOfTickets": stock_data.get("numberOfTickets"),
        "educationalPriceDetail": stock_data.get("educationalPriceDetail"),
    }

    return updatable_fields


def _update_educational_booking_cancellation_limit_date(
    booking: Union[Booking, educational_models.CollectiveBooking], new_beginning_datetime: datetime.datetime
) -> None:
    booking.cancellationLimitDate = compute_educational_booking_cancellation_limit_date(  # type: ignore [assignment]
        new_beginning_datetime, datetime.datetime.utcnow()
    )


def _invalidate_bookings(bookings: list[Booking]) -> list[Booking]:
    for booking in bookings:
        if booking.status is BookingStatus.USED:
            mark_as_unused(booking)
    return bookings


def delete_stock(stock: Stock) -> None:
    validation.check_stock_is_deletable(stock)

    stock.isSoftDeleted = True
    repository.save(stock)

    # the algolia sync for the stock will happen within this function
    cancelled_bookings = cancel_bookings_from_stock_by_offerer(stock)

    logger.info(
        "Deleted stock and cancelled its bookings",
        extra={"stock": stock.id, "bookings": [b.id for b in cancelled_bookings]},
    )
    if cancelled_bookings:
        for booking in cancelled_bookings:
            if not send_booking_cancellation_by_pro_to_beneficiary_email(booking):
                logger.warning(
                    "Could not notify beneficiary about deletion of stock",
                    extra={"stock": stock.id, "booking": booking.id},
                )
        if not send_booking_cancellation_confirmation_by_pro_email(cancelled_bookings):
            logger.warning(
                "Could not notify offerer about deletion of stock",
                extra={"stock": stock.id},
            )

        send_cancel_booking_notification.delay([booking.id for booking in cancelled_bookings])


def create_mediation(
    user: User,
    offer: Offer,
    credit: str,
    image_as_bytes: bytes,
    crop_params: tuple = None,
) -> Mediation:
    # checks image type, min dimensions
    validation.check_image(image_as_bytes)

    mediation = Mediation(
        author=user,
        offer=offer,
        credit=credit,
    )
    # `create_thumb()` requires the object to have an id, so we must save now.
    repository.save(mediation)

    try:
        create_thumb(mediation, image_as_bytes, image_index=0, crop_params=crop_params)

    except Exception as exception:
        logger.exception("An unexpected error was encountered during the thumbnail creation: %s", exception)
        # I could not use savepoints and rollbacks with SQLA
        repository.delete(mediation)
        raise ThumbnailStorageError

    else:
        mediation.thumbCount = 1
        repository.save(mediation)
        # cleanup former thumbnails and mediations

        previous_mediations = (
            Mediation.query.filter(Mediation.offerId == offer.id).filter(Mediation.id != mediation.id).all()
        )
        for previous_mediation in previous_mediations:
            try:
                for thumb_index in range(0, previous_mediation.thumbCount):
                    remove_thumb(previous_mediation, image_index=thumb_index)
            except Exception as exception:  # pylint: disable=broad-except
                logger.exception(
                    "An unexpected error was encountered during the thumbnails deletion for %s: %s",
                    mediation,
                    exception,
                )
            else:
                repository.delete(previous_mediation)

        search.async_index_offer_ids([offer.id])

        return mediation


def update_stock_id_at_providers(venue: Venue, old_siret: str) -> None:
    current_siret = venue.siret

    stocks = (
        Stock.query.join(Offer).filter(Offer.venueId == venue.id).filter(Stock.idAtProviders.endswith(old_siret)).all()
    )

    stock_ids_already_migrated = []
    stocks_to_update = []

    for stock in stocks:
        new_id_at_providers = stock.idAtProviders.replace(old_siret, current_siret)
        if db.session.query(Stock.query.filter_by(idAtProviders=new_id_at_providers).exists()).scalar():
            stock_ids_already_migrated.append(stock.id)
            continue
        stock.idAtProviders = new_id_at_providers
        stocks_to_update.append(stock)

    logger.warning(
        "The following stocks are already migrated from old siret to new siret: [%s]",
        stock_ids_already_migrated,
        extra={"venueId": venue.id, "current_siret": venue.siret, "old_siret": old_siret},
    )

    repository.save(*stocks_to_update)


def get_expense_domains(offer: Offer) -> list[ExpenseDomain]:
    domains = {ExpenseDomain.ALL.value}

    for _deposit_type, versions in deposit_conf.SPECIFIC_CAPS.items():
        for _version, specific_caps in versions.items():  # type: ignore [attr-defined]
            if specific_caps.digital_cap_applies(offer):
                domains.add(ExpenseDomain.DIGITAL.value)
            if specific_caps.physical_cap_applies(offer):
                domains.add(ExpenseDomain.PHYSICAL.value)

    return list(domains)  # type: ignore [arg-type]


def add_criteria_to_offers(criteria: list[Criterion], isbn: Optional[str] = None, visa: Optional[str] = None) -> bool:
    if not isbn and not visa:
        return False

    query = Product.query
    if isbn:
        isbn = isbn.replace("-", "").replace(" ", "")
        query = query.filter(Product.extraData["isbn"].astext == isbn)
    if visa:
        query = query.filter(Product.extraData["visa"].astext == visa)

    products = query.all()
    if not products:
        return False

    offer_ids_query = Offer.query.filter(
        Offer.productId.in_(p.id for p in products), Offer.isActive.is_(True)
    ).with_entities(Offer.id)
    offer_ids = [offer_id for offer_id, in offer_ids_query.all()]

    if not offer_ids:
        return False

    offer_criteria: list[OfferCriterion] = []
    for criterion in criteria:
        logger.info("Adding criterion %s to %d offers", criterion, len(offer_ids))

        offer_criteria.extend(OfferCriterion(offerId=offer_id, criterionId=criterion.id) for offer_id in offer_ids)

    db.session.bulk_save_objects(offer_criteria)
    db.session.commit()

    search.async_index_offer_ids(offer_ids)

    return True


def deactivate_inappropriate_products(isbn: str) -> bool:
    products = Product.query.filter(Product.extraData["isbn"].astext == isbn).all()
    if not products:
        return False

    for product in products:
        product.isGcuCompatible = False
        db.session.add(product)

    offers = Offer.query.filter(Offer.productId.in_(p.id for p in products)).filter(Offer.isActive.is_(True))
    offer_ids = [offer_id for offer_id, in offers.with_entities(Offer.id).all()]
    offers.update(values={"isActive": False}, synchronize_session="fetch")

    try:
        db.session.commit()
    except Exception as exception:  # pylint: disable=broad-except
        logger.exception(
            "Could not mark product and offers as inappropriate: %s",
            extra={"isbn": isbn, "products": [p.id for p in products], "exc": str(exception)},
        )
        return False
    logger.info(
        "Deactivated inappropriate products",
        extra={"isbn": isbn, "products": [p.id for p in products], "offers": offer_ids},
    )

    search.async_index_offer_ids(offer_ids)

    return True


def deactivate_permanently_unavailable_products(isbn: str) -> bool:
    products = Product.query.filter(Product.extraData["isbn"].astext == isbn).all()
    if not products:
        return False

    for product in products:
        product.name = "xxx"
        db.session.add(product)

    offers = Offer.query.filter(Offer.productId.in_(p.id for p in products)).filter(Offer.isActive.is_(True))
    offer_ids = [offer_id for offer_id, in offers.with_entities(Offer.id).all()]
    offers.update(values={"isActive": False, "name": "xxx"}, synchronize_session="fetch")

    try:
        db.session.commit()
    except Exception as exception:  # pylint: disable=broad-except
        logger.exception(
            "Could not mark product and offers as permanently unavailable: %s",
            extra={"isbn": isbn, "products": [p.id for p in products], "exc": str(exception)},
        )
        return False
    logger.info(
        "Deactivated permanently unavailable products",
        extra={"isbn": isbn, "products": [p.id for p in products], "offers": offer_ids},
    )

    search.async_index_offer_ids(offer_ids)

    return True


def set_offer_status_based_on_fraud_criteria(
    offer: Union[educational_models.CollectiveOffer, educational_models.CollectiveOfferTemplate, Offer]
) -> OfferValidationStatus:
    current_config = offers_repository.get_current_offer_validation_config()
    if not current_config:
        return OfferValidationStatus.APPROVED

    minimum_score, validation_rules = parse_offer_validation_config(offer, current_config)

    score = compute_offer_validation_score(validation_rules)
    if score < minimum_score:
        status = OfferValidationStatus.PENDING
    else:
        status = OfferValidationStatus.APPROVED

    logger.info("Computed offer validation", extra={"offer": offer.id, "score": score, "status": status.value})
    return status


def update_pending_offer_validation(offer: Offer, validation_status: OfferValidationStatus) -> bool:
    offer = offer_queries.get_offer_by_id(offer.id)
    if offer.validation != OfferValidationStatus.PENDING:
        logger.info(
            "Offer validation status cannot be updated, initial validation status is not PENDING. %s",
            extra={"offer": offer.id},
        )
        return False
    offer.validation = validation_status  # type: ignore [assignment]
    if validation_status == OfferValidationStatus.APPROVED:
        offer.isActive = True

    try:
        db.session.commit()
    except Exception as exception:  # pylint: disable=broad-except
        logger.exception(
            "Could not update offer validation status: %s",
            extra={"offer": offer.id, "validation_status": validation_status, "exc": str(exception)},
        )
        return False
    search.async_index_offer_ids([offer.id])
    logger.info("Offer validation status updated", extra={"offer": offer.id})
    return True


def import_offer_validation_config(config_as_yaml: str, user: User = None) -> OfferValidationConfig:
    try:
        config_as_dict = yaml.safe_load(config_as_yaml)
        check_validation_config_parameters(config_as_dict, KEY_VALIDATION_CONFIG["init"])
    except (KeyError, ValueError, ScannerError) as error:
        logger.exception(
            "Wrong configuration file format: %s",
            error,
            extra={"exc": str(error)},
        )
        raise WrongFormatInFraudConfigurationFile(str(error))  # type: ignore [arg-type]

    config = OfferValidationConfig(specs=config_as_dict, user=user)
    repository.save(config)
    return config


def _load_product_by_isbn_and_check_is_gcu_compatible_or_raise_error(isbn: str) -> Product:
    product = Product.query.filter(Product.extraData["isbn"].astext == isbn).first()
    if product is None or not product.isGcuCompatible:
        errors = ApiErrors()
        errors.add_error(
            "isbn",
            "Ce produit n’est pas éligible au pass Culture.",
        )
        errors.status_code = 400
        raise errors
    return product


def unindex_expired_offers(process_all_expired: bool = False) -> None:
    """Unindex offers that have expired.

    By default, process offers that have expired within the last 2
    days. For example, if run on Thursday (whatever the time), this
    function handles offers that have expired between Tuesday 00:00
    and Wednesday 23:59 (included).

    If ``process_all_expired`` is true, process... well all expired
    offers.
    """
    start_of_day = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    interval = [start_of_day - datetime.timedelta(days=2), start_of_day]
    if process_all_expired:
        interval[0] = datetime.datetime(2000, 1, 1)  # arbitrary old date

    page = 0
    limit = settings.ALGOLIA_DELETING_OFFERS_CHUNK_SIZE
    while True:
        offers = offers_repository.get_expired_offers(interval)
        offers = offers.offset(page * limit).limit(limit)
        offer_ids = [offer_id for offer_id, in offers.with_entities(Offer.id)]

        if not offer_ids:
            break

        logger.info("[ALGOLIA] Found %d expired offers to unindex", len(offer_ids))
        search.unindex_offer_ids(offer_ids)
        page += 1


def report_offer(user: User, offer: Offer, reason: str, custom_reason: Optional[str]) -> None:
    try:
        # transaction() handles the commit/rollback operations
        #
        # UNIQUE_VIOLATION, CHECK_VIOLATION and STRING_DATA_RIGHT_TRUNCATION
        # errors are specific ones:
        # either the user tried to report the same error twice, which is not
        # allowed, or the client sent a invalid report (eg. OTHER without
        # custom reason / custom reason too long).
        #
        # Other errors are unexpected and are therefore re-raised as is.
        with transaction():
            report = OfferReport(user=user, offer=offer, reason=reason, customReasonContent=custom_reason)
            db.session.add(report)
    except sqla_exc.IntegrityError as error:
        if error.orig.pgcode == UNIQUE_VIOLATION:
            raise OfferAlreadyReportedError() from error
        if error.orig.pgcode == CHECK_VIOLATION:
            raise ReportMalformed() from error
        raise

    if not send_email_reported_offer_by_user(user, offer, reason, custom_reason):
        logger.warning("Could not send email reported offer by user", extra={"user_id": user.id})


def cancel_educational_offer_booking(offer: Offer) -> None:
    if offer.activeStocks is None or len(offer.activeStocks) == 0:
        raise offers_exceptions.StockNotFound()

    if len(offer.activeStocks) > 1:
        raise offers_exceptions.EducationalOfferHasMultipleStocks()

    stock = offer.activeStocks[0]

    # Offer is reindexed in the end of this function
    cancelled_bookings = cancel_bookings_from_stock_by_offerer(stock)

    if len(cancelled_bookings) == 0:
        raise offers_exceptions.NoBookingToCancel()

    logger.info(
        "Deleted stock and cancelled its bookings",
        extra={"stock": stock.id, "bookings": [b.id for b in cancelled_bookings]},
    )
    for booking in cancelled_bookings:
        try:
            adage_client.notify_booking_cancellation_by_offerer(
                data=serialize_educational_booking(booking.educationalBooking)  # type: ignore [arg-type]
            )
        except AdageException as adage_error:
            logger.error(
                "%s Could not notify adage of educational booking cancellation by offerer. Educational institution won't be notified.",
                adage_error.message,
                extra={
                    "bookingId": booking.id,
                    "adage status code": adage_error.status_code,
                    "adage response text": adage_error.response_text,
                },
            )
        except ValidationError:
            logger.exception(
                "Could not notify adage of prebooking, hence send confirmation email to educational institution, as educationalBooking serialization failed.",
                extra={
                    "bookingId": booking.id,
                },
            )
    if not send_booking_cancellation_confirmation_by_pro_email(cancelled_bookings):
        logger.warning(
            "Could not notify offerer about deletion of stock",
            extra={"stock": stock.id},
        )


def create_collective_shadow_offer(stock_data: EducationalOfferShadowStockBodyModel, user: User, offer_id: str):  # type: ignore [no-untyped-def]
    offer = Offer.query.filter_by(id=offer_id).options(sqla_orm.joinedload(Offer.stocks)).one()
    stock = create_educational_shadow_stock_and_set_offer_showcase(stock_data, user, offer)
    create_collective_offer_template_and_delete_collective_offer(offer, stock, user)
    return stock


def create_collective_offer_template_and_delete_collective_offer(offer: Offer, stock: Stock, user: User) -> None:
    collective_offer = educational_models.CollectiveOffer.query.filter_by(offerId=offer.id).one_or_none()
    if collective_offer is None:
        raise offers_exceptions.CollectiveOfferNotFound()

    collective_offer_template = educational_models.CollectiveOfferTemplate.create_from_collective_offer(
        collective_offer, price_detail=stock.educationalPriceDetail
    )
    db.session.delete(collective_offer)
    db.session.add(collective_offer_template)
    db.session.commit()

    if FeatureToggle.ENABLE_NEW_COLLECTIVE_MODEL.is_active():
        if offer.validation == OfferValidationStatus.DRAFT:
            _update_offer_fraud_information(collective_offer_template, user)
    else:
        # the offer validation is copied from the offer. The only problem is when the offer is in draft as the fraud is
        # not enabled of collectiveOfferTemplate it will stay in draft. Therefor we force its status
        if collective_offer_template.validation == OfferValidationStatus.DRAFT:
            collective_offer_template.validation = OfferValidationStatus.APPROVED  # type: ignore [assignment]
            collective_offer_template.lastValidationDate = datetime.datetime.utcnow()
            collective_offer_template.lastValidationType = OfferValidationType.AUTO  # type: ignore [assignment]

    logger.info(
        "Collective offer template has been created and regular collective offer deleted if applicable",
        extra={"collectiveOfferTemplate": collective_offer_template.id, "offer": offer.id},
    )


def cancel_collective_offer_booking(offer: Offer) -> None:
    collective_offer = CollectiveOffer.query.filter(CollectiveOffer.offerId == offer.id).first()

    if collective_offer is None:
        # FIXME (MathildeDuboille - 2022-03-03): raise an error once this code is on production
        # and all data has been migrated to the new models
        return

    if collective_offer.collectiveStock is None:
        # FIXME (MathildeDuboille - 2022-03-03): raise an error once this code is on production
        # and all data has been migrated to the new models
        return

    collective_stock = collective_offer.collectiveStock

    # Offer is reindexed in the end of this function
    cancelled_booking = cancel_collective_booking_from_stock_by_offerer(collective_stock)

    if cancelled_booking is None:
        # FIXME (MathildeDuboille - 2022-03-03): raise an error once this code is on production
        # and all data has been migrated to the new models
        return

    logger.info(
        "Deleted collective stock and cancelled its collective booking",
        extra={"stock": collective_stock.id, "collective_booking": cancelled_booking.id},
    )

    if FeatureToggle.ENABLE_NEW_COLLECTIVE_MODEL.is_active():
        try:
            adage_client.notify_booking_cancellation_by_offerer(data=serialize_collective_booking(cancelled_booking))
        except AdageException as adage_error:
            logger.error(
                "%s Could not notify adage of collective booking cancellation by offerer. Educational institution won't be notified.",
                adage_error.message,
                extra={
                    "collectiveBookingId": cancelled_booking.id,
                    "adage status code": adage_error.status_code,
                    "adage response text": adage_error.response_text,
                },
            )
        except ValidationError:
            logger.exception(
                "Could not notify adage of prebooking, hence send confirmation email to educational institution, as educationalBooking serialization failed.",
                extra={
                    "collectiveBookingId": cancelled_booking.id,
                },
            )
        if not send_booking_cancellation_confirmation_by_pro_email([cancelled_booking]):
            logger.warning(
                "Could not notify offerer about deletion of stock",
                extra={"collectiveStock": collective_stock.id},
            )


def create_educational_shadow_stock_and_set_offer_showcase(
    stock_data: EducationalOfferShadowStockBodyModel, user: User, offer: Offer
) -> Stock:
    # When creating a showcase offer we need to create a shadow stock.
    # We prefill the stock information with false data.
    # This code will disappear when the new collective offer model is implemented
    beginning = datetime.datetime(2030, 1, 1)
    booking_limit_datetime = datetime.datetime(2030, 1, 1)
    total_price = 1
    number_of_tickets = 1
    educational_price_detail = stock_data.educational_price_detail

    if len(offer.activeStocks) > 0:
        raise educational_exceptions.EducationalStockAlreadyExists()

    if not offer.isEducational:
        raise educational_exceptions.OfferIsNotEducational(offer.id)
    validation.check_validation_status(offer)

    stock = Stock(
        offer=offer,
        beginningDatetime=beginning,
        bookingLimitDatetime=booking_limit_datetime,
        price=total_price,
        numberOfTickets=number_of_tickets,
        educationalPriceDetail=educational_price_detail,
        quantity=1,
    )
    repository.save(stock)
    logger.info("Educational shadow stock has been created", extra={"offer": offer.id})

    extra_data = copy.deepcopy(offer.extraData)
    extra_data["isShowcase"] = True  # type: ignore [index, call-overload]
    offer.extraData = extra_data
    repository.save(offer)

    if offer.validation == OfferValidationStatus.DRAFT:
        _update_offer_fraud_information(offer, user)

    search.async_index_offer_ids([offer.id])

    return stock


def transform_shadow_stock_into_educational_stock_and_create_collective_offer(
    stock_id: str, stock_data: EducationalStockCreationBodyModel, user: User
) -> Stock:
    offer = offers_repository.get_educational_offer_by_id((stock_data.offer_id))  # type: ignore [arg-type]
    stock = transform_shadow_stock_into_educational_stock(stock_id, stock_data, offer, user)
    create_collective_offer_and_delete_collective_offer_template(offer)
    educational_api.create_collective_stock(stock_data=stock_data, user=user, legacy_id=stock.id)
    return stock


def create_collective_offer_and_delete_collective_offer_template(offer: Offer) -> None:
    collective_offer_template = educational_models.CollectiveOfferTemplate.query.filter_by(
        offerId=offer.id
    ).one_or_none()

    if collective_offer_template is None:
        # FIXME (cgaunet, 2022-03-02): Raise once migration script has been launched (PC-13427)
        logger.info(
            "Collective offer template not found. Collective offer will be created from old offer model",
            extra={"offer": offer.id},
        )
        collective_offer = educational_models.CollectiveOffer.create_from_offer(
            offer,
        )
    else:
        collective_offer = educational_models.CollectiveOffer.create_from_collective_offer_template(
            collective_offer_template
        )
        db.session.delete(collective_offer_template)

    db.session.add(collective_offer)
    db.session.commit()


def transform_shadow_stock_into_educational_stock(
    stock_id: str, stock_data: EducationalStockCreationBodyModel, offer: Offer, user: User
) -> Stock:
    if offer.extraData.get("isShowcase") is not True:  # type: ignore [union-attr]
        raise educational_exceptions.OfferIsNotShowcase()

    shadow_stock = offers_repository.get_non_deleted_stock_by_id(stock_id)  # type: ignore [arg-type]
    validation.check_stock_is_deletable(shadow_stock)
    shadow_stock.isSoftDeleted = True
    db.session.add(shadow_stock)

    stock = create_educational_stock(stock_data, user)
    # commit the changes on shadow_stock once the new stock is created
    db.session.commit()

    extra_data = copy.deepcopy(offer.extraData)
    extra_data["isShowcase"] = False  # type: ignore [index, call-overload]
    offer.extraData = extra_data
    repository.save(offer)

    return stock


def edit_shadow_stock(stock: Stock, stock_data: dict) -> Stock:
    if not stock.offer.isEducational:
        raise educational_exceptions.OfferIsNotEducational(stock.offerId)

    if stock.offer.extraData.get("isShowcase") is not True:  # type: ignore [union-attr]
        raise educational_exceptions.OfferIsNotShowcase()

    check_shadow_stock_is_editable(stock)

    with transaction():
        stock = offers_repository.get_and_lock_stock(stock.id)
        if stock_data.get("educational_price_detail") is not None:
            stock.educationalPriceDetail = stock_data["educational_price_detail"]
        db.session.add(stock)
        db.session.commit()

    logger.info("Stock has been updated", extra={"stock": stock.id})

    search.async_index_offer_ids([stock.offerId])

    return stock
