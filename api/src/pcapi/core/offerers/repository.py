from typing import Iterable
from typing import Optional

from flask_sqlalchemy import BaseQuery
import sqlalchemy as sqla
import sqlalchemy.orm as sqla_orm

from pcapi.core.offers.models import Offer
from pcapi.core.users.models import User
from pcapi.domain.ts_vector import create_filter_matching_all_keywords_in_any_model
from pcapi.domain.ts_vector import create_get_filter_matching_ts_query_in_any_model
from pcapi.models import db
from pcapi.models.bank_information import BankInformation
from pcapi.models.bank_information import BankInformationStatus
from pcapi.models.offer_mixin import OfferStatus
from pcapi.models.offer_mixin import OfferValidationStatus
from pcapi.utils.human_ids import dehumanize

from . import exceptions
from . import models


def get_all_venue_labels() -> list[models.VenueLabel]:
    return models.VenueLabel.query.all()


def get_all_offerers_for_user(
    user: User,
    validated: bool = None,
    validated_for_user: bool = None,
    keywords: str = None,
) -> sqla_orm.Query:
    """Return a query of matching, accessible offerers.

    **WARNING:** this function may return more than one row per
    offerer (for offerers that have multiple user offerers and/or
    multiple venues). Deduplication should be done by the caller (with
    `distinct()`). This function cannot call `distinct()` itself
    because it does not know how the caller wants to sort results (and
    `distinct` and `order by` clauses must match).
    """
    query = models.Offerer.query.filter(models.Offerer.isActive.is_(True))

    if not user.has_admin_role:
        query = query.join(models.UserOfferer, models.UserOfferer.offererId == models.Offerer.id).filter(
            models.UserOfferer.userId == user.id
        )

    if validated is not None:
        if validated:
            query = query.filter(models.Offerer.validationToken.is_(None))
        else:
            query = query.filter(models.Offerer.validationToken.isnot(None))

    if validated_for_user is not None:
        if user.has_admin_role:
            query = query.join(models.UserOfferer, models.UserOfferer.offererId == models.Offerer.id)
        else:
            pass  # we already JOINed above.
        if validated_for_user:
            query = query.filter(models.UserOfferer.validationToken.is_(None))
        else:
            query = query.filter(models.UserOfferer.validationToken.isnot(None))

    if keywords:
        query = filter_offerers_with_keywords_string(query, keywords)

    return query


def get_offer_counts_by_venue(venue_ids: Iterable[int]) -> dict[int, int]:
    """Return a dictionary with the number of non-draft offers for each
    requested venue.

    Venues that do not have any offers are not included in the
    returned dictionary.
    """
    return dict(
        Offer.query.filter(
            Offer.validation != OfferValidationStatus.DRAFT,
            Offer.venueId.in_(venue_ids),
        )
        .with_entities(Offer.venueId, sqla.func.count())
        .group_by(Offer.venueId)
        .all()
    )


def get_filtered_venues(
    pro_user_id: int,
    user_is_admin: bool,
    active_offerers_only: Optional[bool] = False,
    offerer_id: Optional[int] = None,
    validated_offerer: Optional[bool] = None,
    validated_offerer_for_user: Optional[bool] = None,
) -> list[models.Venue]:
    query = (
        models.Venue.query.join(models.Offerer, models.Offerer.id == models.Venue.managingOffererId)
        .join(models.UserOfferer, models.UserOfferer.offererId == models.Offerer.id)
        .options(sqla_orm.joinedload(models.Venue.managingOfferer))
        .options(sqla_orm.joinedload(models.Venue.businessUnit))
    )
    if not user_is_admin:
        query = query.filter(models.UserOfferer.userId == pro_user_id)

    if validated_offerer is not None:
        if validated_offerer:
            query = query.filter(models.Offerer.validationToken.is_(None))
        else:
            query = query.filter(models.Offerer.validationToken.isnot(None))
    if validated_offerer_for_user is not None:
        if validated_offerer_for_user:
            query = query.filter(models.UserOfferer.validationToken.is_(None))
        else:
            query = query.filter(models.UserOfferer.validationToken.isnot(None))

    if active_offerers_only:
        query = query.filter(models.Offerer.isActive.is_(True))

    if offerer_id:
        query = query.filter(models.Venue.managingOffererId == offerer_id)

    return query.order_by(models.Venue.name).all()


def get_api_key_prefixes(offerer_id: int) -> list[str]:
    return [
        prefix or value[:8]
        for prefix, value in models.ApiKey.query.filter_by(offererId=offerer_id)
        .with_entities(models.ApiKey.prefix, models.ApiKey.value)
        .all()
        if prefix or value
    ]


def find_offerer_by_siren(siren: str) -> Optional[models.Offerer]:
    return models.Offerer.query.filter_by(siren=siren).one_or_none()


def find_offerer_by_validation_token(token: str) -> Optional[models.UserOfferer]:
    return models.Offerer.query.filter_by(validationToken=token).one_or_none()


def find_user_offerer_by_validation_token(token: str) -> Optional[models.UserOfferer]:
    return models.UserOfferer.query.filter_by(validationToken=token).one_or_none()


def find_all_user_offerers_by_offerer_id(offerer_id: int) -> list[models.UserOfferer]:
    return models.UserOfferer.query.filter_by(offererId=offerer_id).all()


def filter_query_where_user_is_user_offerer_and_is_validated(query, user):  # type: ignore [no-untyped-def]
    return query.join(models.UserOfferer).filter_by(user=user).filter(models.UserOfferer.validationToken.is_(None))


def find_user_offerers(user: int, offerer_id: str) -> models.UserOfferer:
    return models.UserOfferer.query.filter_by(user=user, offererId=dehumanize(offerer_id)).all()


def find_venue_by_id(venue_id: int) -> Optional[models.Venue]:
    return models.Venue.query.filter_by(id=venue_id).one_or_none()


def find_venue_by_siret(siret: str) -> Optional[models.Venue]:
    return models.Venue.query.filter_by(siret=siret).one_or_none()


def find_venue_by_managing_offerer_id(offerer_id: int) -> Optional[models.Venue]:
    return models.Venue.query.filter_by(managingOffererId=offerer_id).first()


def find_virtual_venue_by_offerer_id(offerer_id: int) -> Optional[models.Venue]:
    return models.Venue.query.filter_by(managingOffererId=offerer_id, isVirtual=True).first()


def find_active_venues_by_booking_email(email: str) -> list[models.Venue]:
    return (
        models.Venue.query.filter_by(bookingEmail=email)
        .join(models.Offerer)
        .filter(models.Offerer.isActive == True)
        .all()
    )


def has_physical_venue_without_draft_or_accepted_bank_information(offerer_id: int) -> bool:
    return db.session.query(
        models.Venue.query.outerjoin(BankInformation)
        .filter(models.Venue.managingOffererId == offerer_id)
        .filter(models.Venue.isVirtual.is_(False))
        .filter(
            sqla.or_(
                BankInformation.status.notin_((BankInformationStatus.DRAFT, BankInformationStatus.ACCEPTED)),
                models.Venue.bankInformation == None,
            )
        )
        .exists()
    ).scalar()


def has_digital_venue_with_at_least_one_offer(offerer_id: int) -> bool:
    return db.session.query(
        models.Venue.query.join(Offer, models.Venue.id == Offer.venueId)
        .filter(models.Venue.managingOffererId == offerer_id)
        .filter(models.Venue.isVirtual.is_(True))
        .exists()
    ).scalar()


get_filter_matching_ts_query_for_offerer = create_get_filter_matching_ts_query_in_any_model(
    models.Offerer, models.Venue
)


def get_by_offer_id(offer_id: int) -> Optional[models.Offerer]:
    offerer = models.Offerer.query.join(models.Venue).join(Offer).filter_by(id=offer_id).one_or_none()
    if not offerer:
        raise exceptions.CannotFindOffererForOfferId()
    return offerer


def find_new_offerer_user_email(offerer_id: int) -> str:
    result_tuple = models.UserOfferer.query.filter_by(offererId=offerer_id).join(User).with_entities(User.email).first()
    if result_tuple:
        return result_tuple[0]
    raise exceptions.CannotFindOffererUserEmail()


def filter_offerers_with_keywords_string(query: BaseQuery, keywords_string: str) -> BaseQuery:
    keywords_filter = create_filter_matching_all_keywords_in_any_model(
        get_filter_matching_ts_query_for_offerer, keywords_string
    )
    subquery = (
        models.Offerer.query.outerjoin(models.Offerer.managedVenues)
        .filter(keywords_filter)
        .with_entities(models.Offerer.id)
        .subquery()
    )
    query = query.filter(models.Offerer.id.in_(subquery))
    return query


def check_if_siren_already_exists(siren: str) -> bool:
    return db.session.query(db.session.query(models.Offerer.id).filter(models.Offerer.siren == siren).exists())


def find_siren_by_offerer_id(offerer_id: int) -> str:
    siren = models.Offerer.query.filter_by(id=offerer_id).with_entities(models.Offerer.siren).scalar()

    if siren:
        return siren

    raise exceptions.CannotFindOffererSiren


def venues_have_offers(*venues: models.Venue) -> bool:
    """At least one venue which has email as bookingEmail has at least one active offer"""
    return db.session.query(
        Offer.query.filter(
            Offer.venueId.in_([venue.id for venue in venues]), Offer.status == OfferStatus.ACTIVE.name
        ).exists()
    ).scalar()


def find_venues_by_managing_offerer_id(offerer_id: int) -> list[models.Venue]:
    return models.Venue.query.filter_by(managingOffererId=offerer_id).all()


def find_venues_by_offerers(*offerers: models.Offerer) -> list[models.Venue]:
    """Get all venues managed by any offerer given in arguments"""
    return models.Venue.query.filter(models.Venue.managingOffererId.in_([offerer.id for offerer in offerers])).all()
