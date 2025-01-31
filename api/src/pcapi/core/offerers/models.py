from datetime import datetime
import enum
import typing
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import TEXT
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import case
from sqlalchemy import cast
from sqlalchemy import func
from sqlalchemy.dialects.postgresql.json import JSONB
from sqlalchemy.event import listens_for
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import aliased
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression
from sqlalchemy.sql.sqltypes import CHAR
from sqlalchemy.sql.sqltypes import LargeBinary
from werkzeug.utils import cached_property

from pcapi.connectors.api_entreprises import get_offerer_legal_category
from pcapi.domain.postal_code.postal_code import OVERSEAS_DEPARTEMENT_CODE_START
from pcapi.domain.postal_code.postal_code import PostalCode
from pcapi.domain.ts_vector import create_ts_vector_and_table_args
from pcapi.models import Model
from pcapi.models import db
from pcapi.models.bank_information import BankInformationStatus
from pcapi.models.deactivable_mixin import DeactivableMixin
from pcapi.models.has_address_mixin import HasAddressMixin
from pcapi.models.has_thumb_mixin import HasThumbMixin
from pcapi.models.needs_validation_mixin import NeedsValidationMixin
from pcapi.models.pc_object import PcObject
from pcapi.models.providable_mixin import ProvidableMixin
from pcapi.utils import crypto
from pcapi.utils.date import CUSTOM_TIMEZONES
from pcapi.utils.date import METROPOLE_TIMEZONE
from pcapi.utils.date import get_department_timezone
from pcapi.utils.date import get_postal_code_timezone
from pcapi.utils.human_ids import humanize


CONSTRAINT_CHECK_IS_VIRTUAL_XOR_HAS_ADDRESS = """
(
    "isVirtual" IS TRUE
    AND (address IS NULL AND "postalCode" IS NULL AND city IS NULL AND "departementCode" IS NULL)
)
OR
(
    "isVirtual" IS FALSE
    AND siret is NOT NULL
    AND ("postalCode" IS NOT NULL AND city IS NOT NULL AND "departementCode" IS NOT NULL)
)
OR
(
    "isVirtual" IS FALSE
    AND (siret is NULL and comment is NOT NULL)
    AND (address IS NOT NULL AND "postalCode" IS NOT NULL AND city IS NOT NULL AND "departementCode" IS NOT NULL)
)

"""

CONSTRAINT_CHECK_HAS_SIRET_XOR_HAS_COMMENT_XOR_IS_VIRTUAL = """
    (siret IS NULL AND comment IS NULL AND "isVirtual" IS TRUE)
    OR (siret IS NULL AND comment IS NOT NULL AND "isVirtual" IS FALSE)
    OR (siret IS NOT NULL AND "isVirtual" IS FALSE)
"""

VENUE_TYPE_CODE_MAPPING = {
    "VISUAL_ARTS": "Arts visuels, arts plastiques et galeries",
    "CULTURAL_CENTRE": "Centre culturel",
    "ARTISTIC_COURSE": "Cours et pratique artistiques",
    "SCIENTIFIC_CULTURE": "Culture scientifique",
    "FESTIVAL": "Festival",
    "GAMES": "Jeux / Jeux vidéos",
    "BOOKSTORE": "Librairie",
    "LIBRARY": "Bibliothèque ou médiathèque",
    "MUSEUM": "Musée",
    "RECORD_STORE": "Musique - Disquaire",
    "MUSICAL_INSTRUMENT_STORE": "Musique - Magasin d’instruments",
    "CONCERT_HALL": "Musique - Salle de concerts",
    "DIGITAL": "Offre numérique",
    "PATRIMONY_TOURISM": "Patrimoine et tourisme",
    "MOVIE": "Cinéma - Salle de projections",
    "PERFORMING_ARTS": "Spectacle vivant",
    "CREATIVE_ARTS_STORE": "Magasin arts créatifs",
    "ADMINISTRATIVE": "Lieu administratif",
    "OTHER": "Autre",
}


class BaseVenueTypeCode(enum.Enum):
    @classmethod
    def __get_validators__(cls):  # type: ignore [no-untyped-def]
        cls.lookup = {v: k.name for v, k in cls.__members__.items()}
        yield cls.validate

    @classmethod
    def validate(cls, v):  # type: ignore [no-untyped-def]
        try:
            return cls.lookup[v]
        except KeyError:
            raise ValueError(f"{v}: invalide")


VenueTypeCode = enum.Enum("VenueTypeCode", VENUE_TYPE_CODE_MAPPING, type=BaseVenueTypeCode)  # type: ignore [misc]
VenueTypeCodeKey = enum.Enum(  # type: ignore [misc]
    "VenueTypeCodeKey",
    {name: name for name, _ in VENUE_TYPE_CODE_MAPPING.items()},
)


class Venue(PcObject, Model, HasThumbMixin, HasAddressMixin, ProvidableMixin, NeedsValidationMixin):  # type: ignore [valid-type, misc]
    __tablename__ = "venue"

    id = Column(BigInteger, primary_key=True)

    name = Column(String(140), nullable=False)

    siret = Column(String(14), nullable=True, unique=True)

    departementCode = Column(String(3), nullable=True)

    latitude = Column(Numeric(8, 5), nullable=True)

    longitude = Column(Numeric(8, 5), nullable=True)

    venueProviders = relationship("VenueProvider", back_populates="venue")  # type: ignore [misc]

    managingOffererId = Column(BigInteger, ForeignKey("offerer.id"), nullable=False, index=True)

    managingOfferer = relationship("Offerer", foreign_keys=[managingOffererId], backref="managedVenues")

    bookingEmail = Column(String(120), nullable=True)

    postalCode = Column(String(6), nullable=True)  # type: ignore [assignment]

    city = Column(String(50), nullable=True)  # type: ignore [assignment]

    publicName = Column(String(255), nullable=True)

    isVirtual = Column(
        Boolean,
        CheckConstraint(CONSTRAINT_CHECK_IS_VIRTUAL_XOR_HAS_ADDRESS, name="check_is_virtual_xor_has_address"),
        nullable=False,
        default=False,
        server_default=expression.false(),
    )

    isPermanent = Column(
        Boolean,
        nullable=True,
        default=False,
    )

    comment = Column(
        TEXT,
        CheckConstraint(
            CONSTRAINT_CHECK_HAS_SIRET_XOR_HAS_COMMENT_XOR_IS_VIRTUAL, name="check_has_siret_xor_comment_xor_isVirtual"
        ),
        nullable=True,
    )

    collectiveOffers = relationship("CollectiveOffer", back_populates="venue")  # type: ignore [misc]

    collectiveOfferTemplates = relationship("CollectiveOfferTemplate", back_populates="venue")  # type: ignore [misc]

    venueTypeId = Column(Integer, ForeignKey("venue_type.id"), nullable=True)

    venueType = relationship("VenueType", foreign_keys=[venueTypeId])

    venueTypeCode = Column(sa.Enum(VenueTypeCode, create_constraint=False), nullable=True, default=VenueTypeCode.OTHER)  # type: ignore [attr-defined]

    venueLabelId = Column(Integer, ForeignKey("venue_label.id"), nullable=True)

    venueLabel = relationship("VenueLabel", foreign_keys=[venueLabelId])

    dateCreated = Column(DateTime, nullable=False, default=datetime.utcnow)

    withdrawalDetails = Column(Text, nullable=True)

    audioDisabilityCompliant = Column(Boolean, nullable=True)

    mentalDisabilityCompliant = Column(Boolean, nullable=True)

    motorDisabilityCompliant = Column(Boolean, nullable=True)

    visualDisabilityCompliant = Column(Boolean, nullable=True)

    description = Column(Text, nullable=True)

    contact = relationship("VenueContact", back_populates="venue", uselist=False)

    businessUnitId = Column(Integer, ForeignKey("business_unit.id"), nullable=True)
    businessUnit = relationship("BusinessUnit", foreign_keys=[businessUnitId], backref="venues")  # type: ignore [misc]

    # bannerUrl should provide a safe way to retrieve the banner,
    # whereas bannerMeta should provide extra information that might be
    # helpful like image type, author, etc. that can change over time.
    bannerUrl = Column(Text, nullable=True)

    bannerMeta = Column(MutableDict.as_mutable(JSONB), nullable=True)

    thumb_path_component = "venues"

    criteria = sa.orm.relationship(  # type: ignore [misc]
        "Criterion", backref=db.backref("venue_criteria", lazy="dynamic"), secondary="venue_criterion"
    )

    @property
    def is_eligible_for_search(self) -> bool:
        return self.isPermanent and self.managingOfferer.isActive and self.venueTypeCode != VenueTypeCode.ADMINISTRATIVE  # type: ignore [return-value, attr-defined]

    def store_departement_code(self) -> None:
        self.departementCode = PostalCode(self.postalCode).get_departement_code()  # type: ignore [has-type]

    @property
    def bic(self) -> Optional[str]:
        return self.bankInformation.bic if self.bankInformation else None

    @property
    def iban(self) -> Optional[str]:
        return self.bankInformation.iban if self.bankInformation else None

    @property
    def demarchesSimplifieesApplicationId(self) -> Optional[int]:
        if not self.bankInformation:
            return None

        if self.bankInformation.status not in (
            BankInformationStatus.DRAFT,
            BankInformationStatus.ACCEPTED,
        ):
            return None

        return self.bankInformation.applicationId

    @property
    def demarchesSimplifieesIsDraft(self):  # type: ignore [no-untyped-def]
        return self.bankInformation and self.bankInformation.status == BankInformationStatus.DRAFT

    @property
    def demarchesSimplifieesIsAccepted(self):  # type: ignore [no-untyped-def]
        return self.bankInformation and self.bankInformation.status == BankInformationStatus.ACCEPTED

    @property
    def nApprovedOffers(self) -> int:  # used in validation rule, do not remove
        from pcapi.core.offers.models import OfferValidationStatus

        return len([offer for offer in self.offers if offer.validation == OfferValidationStatus.APPROVED])

    @property
    def isBusinessUnitMainVenue(self) -> bool:
        if self.businessUnit and self.businessUnit.siret:
            return self.siret == self.businessUnit.siret
        return False

    @property
    def thumbUrl(self):  # type: ignore [no-untyped-def]
        """
        Override to discard the thumbCount column: not used by Venues
        which have at most one banner (thumb).
        """
        return "{}/{}/{}".format(self.thumb_base_url, self.thumb_path_component, humanize(self.id))

    @hybrid_property
    def timezone(self) -> str:
        if self.departementCode is None:
            return get_postal_code_timezone(self.managingOfferer.postalCode)
        return get_department_timezone(self.departementCode)

    @timezone.expression  # type: ignore [no-redef]
    def timezone(cls):  # pylint: disable=no-self-argument
        offerer_alias = aliased(Offerer)
        return case(
            [
                (
                    cls.departementCode.is_(None),
                    case(
                        CUSTOM_TIMEZONES,
                        value=db.session.query(offerer_alias.departementCode)
                        .filter(cls.managingOffererId == offerer_alias.id)
                        .as_scalar(),
                        else_=METROPOLE_TIMEZONE,
                    ),
                )
            ],
            else_=case(CUSTOM_TIMEZONES, value=cls.departementCode, else_=METROPOLE_TIMEZONE),
        )

    def field_exists_and_has_changed(self, field: str, value: typing.Any) -> typing.Any:
        if field not in type(self).__table__.columns:
            raise ValueError(f"Unknown field {field} for model {type(self)}")
        return getattr(self, field) != value


class VenueLabel(PcObject, Model):  # type: ignore [valid-type, misc]
    __tablename__ = "venue_label"

    label = Column(String(100), nullable=False)

    venue = relationship("Venue")


class VenueType(PcObject, Model):  # type: ignore [valid-type, misc]
    label = Column(String(100), nullable=False)

    venue = relationship("Venue")


class VenueContact(PcObject, Model):  # type: ignore [valid-type, misc]
    __tablename__ = "venue_contact"

    id = Column(BigInteger, primary_key=True)

    venueId = Column(BigInteger, ForeignKey("venue.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)

    venue = relationship("Venue", foreign_keys=[venueId], back_populates="contact")

    email = Column(String(256), nullable=True)

    website = Column(String(256), nullable=True)

    phone_number = Column(String(64), nullable=True)

    social_medias = Column(MutableDict.as_mutable(JSONB), nullable=False, default={}, server_default="{}")

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(venueid={self.venueId!r}, "
            f"email={self.email!r}, "
            f"phone_number={self.phone_number!r}, "
            f"social_medias={self.social_medias!r})"
        )

    def field_exists_and_has_changed(self, field: str, value: typing.Any) -> typing.Any:
        if field not in type(self).__table__.columns:
            raise ValueError(f"Unknown field {field} for model {type(self)}")
        return getattr(self, field) != value


class VenueCriterion(PcObject, Model):  # type: ignore [valid-type, misc]
    venueId = Column(BigInteger, ForeignKey("venue.id", ondelete="CASCADE"), index=True, nullable=False)

    venue = relationship("Venue", foreign_keys=[venueId])

    criterionId = Column(BigInteger, ForeignKey("criterion.id", ondelete="CASCADE"), nullable=False, index=True)

    criterion = relationship("Criterion", foreign_keys=[criterionId])  # type: ignore [misc]

    __table_args__ = (
        UniqueConstraint(
            "venueId",
            "criterionId",
            name="unique_venue_criterion",
        ),
    )


@listens_for(Venue, "before_insert")
def before_insert(mapper, connect, self):  # type: ignore [no-untyped-def]
    _fill_departement_code_from_postal_code(self)


@listens_for(Venue, "before_update")
def before_update(mapper, connect, self):  # type: ignore [no-untyped-def]
    _fill_departement_code_from_postal_code(self)


def _fill_departement_code_from_postal_code(self):  # type: ignore [no-untyped-def]
    if not self.isVirtual:
        if not self.postalCode:
            raise IntegrityError(None, None, None)
        self.store_departement_code()


ts_indexes = [
    ("idx_venue_fts_name", Venue.name),
    (
        "idx_venue_fts_publicName",
        Venue.publicName,
    ),
    ("idx_venue_fts_address", Venue.address),
    ("idx_venue_fts_siret", Venue.siret),
    ("idx_venue_fts_city", Venue.city),  # type: ignore [has-type]
]

(Venue.__ts_vectors__, Venue.__table_args__) = create_ts_vector_and_table_args(ts_indexes)


class Offerer(
    PcObject,
    Model,  # type: ignore [valid-type, misc]
    HasThumbMixin,
    HasAddressMixin,
    ProvidableMixin,
    NeedsValidationMixin,
    DeactivableMixin,
):
    id = Column(BigInteger, primary_key=True)

    dateCreated = Column(DateTime, nullable=False, default=datetime.utcnow)

    name = Column(String(140), nullable=False)

    users = relationship("User", secondary="user_offerer")  # type: ignore [misc]

    siren = Column(
        String(9), nullable=True, unique=True
    )  # FIXME: should not be nullable, is until we have all SIRENs filled in the DB

    dateValidated = Column(DateTime, nullable=True, default=None)

    tags = sa.orm.relationship(
        "OffererTag", backref=db.backref("offerer_tags", lazy="dynamic"), secondary="offerer_tag_mapping"
    )

    thumb_path_component = "offerers"

    @property
    def bic(self):  # type: ignore [no-untyped-def]
        return self.bankInformation.bic if self.bankInformation else None

    @property
    def iban(self):  # type: ignore [no-untyped-def]
        return self.bankInformation.iban if self.bankInformation else None

    @property
    def demarchesSimplifieesApplicationId(self):  # type: ignore [no-untyped-def]
        if not self.bankInformation:
            return None

        if self.bankInformation.status not in (
            BankInformationStatus.DRAFT,
            BankInformationStatus.ACCEPTED,
        ):
            return None

        return self.bankInformation.applicationId

    @hybrid_property
    def departementCode(self):
        return PostalCode(self.postalCode).get_departement_code()

    @departementCode.expression  # type: ignore [no-redef]
    def departementCode(cls):  # pylint: disable=no-self-argument
        return case(
            [
                (
                    cast(func.substring(cls.postalCode, 1, 2), Integer) >= OVERSEAS_DEPARTEMENT_CODE_START,
                    func.substring(cls.postalCode, 1, 3),
                )
            ],
            else_=func.substring(cls.postalCode, 1, 2),
        )

    @cached_property
    def legal_category(self) -> dict:
        return get_offerer_legal_category(self)


offerer_ts_indexes = [
    ("idx_offerer_fts_name", Offerer.name),
    ("idx_offerer_fts_address", Offerer.address),
    ("idx_offerer_fts_siret", Offerer.siren),
]

(Offerer.__ts_vectors__, Offerer.__table_args__) = create_ts_vector_and_table_args(offerer_ts_indexes)


class UserOfferer(PcObject, Model, NeedsValidationMixin):  # type: ignore [valid-type, misc]
    userId = Column(BigInteger, ForeignKey("user.id"), primary_key=True)
    user = relationship("User", foreign_keys=[userId], backref=backref("UserOfferers"))  # type: ignore [misc]
    offererId = Column(BigInteger, ForeignKey("offerer.id"), index=True, primary_key=True)
    offerer = relationship("Offerer", foreign_keys=[offererId], backref=backref("UserOfferers"))

    __table_args__ = (
        UniqueConstraint(
            "userId",
            "offererId",
            name="unique_user_offerer",
        ),
    )


class ApiKey(PcObject, Model):  # type: ignore [valid-type, misc]
    # TODO: remove value colum when legacy keys are migrated
    value = Column(CHAR(64), index=True, nullable=True)

    offererId = Column(BigInteger, ForeignKey("offerer.id"), index=True, nullable=False)

    offerer = relationship("Offerer", foreign_keys=[offererId], backref=backref("apiKeys"))

    dateCreated = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())

    prefix = Column(Text, nullable=True, unique=True)

    secret = Column(LargeBinary, nullable=True)

    def check_secret(self, clear_text: str) -> bool:
        return crypto.check_password(clear_text, self.secret)  # type: ignore [arg-type]


class OffererTag(PcObject, Model):  # type: ignore [valid-type, misc]
    """
    Tags on offerers are only used in backoffice, set to help for filtering and analytics in metabase.
    There is currently no display or impact in mobile and web apps.
    """

    __tablename__ = "offerer_tag"

    name = Column(String(140), nullable=False, unique=True)

    def __repr__(self):  # type: ignore [no-untyped-def]
        return "%s" % self.name


class OffererTagMapping(PcObject, Model):  # type: ignore [valid-type, misc]
    __tablename__ = "offerer_tag_mapping"

    offererId = Column(BigInteger, ForeignKey("offerer.id", ondelete="CASCADE"), index=True, nullable=False)

    offerer = relationship("Offerer", foreign_keys=[offererId])

    tagId = Column(BigInteger, ForeignKey("offerer_tag.id", ondelete="CASCADE"), index=True, nullable=False)

    tag = relationship("OffererTag", foreign_keys=[tagId])

    __table_args__ = (
        UniqueConstraint(
            "offererId",
            "tagId",
            name="unique_offerer_tag",
        ),
    )
