import datetime
import decimal
import secrets

import factory
from factory.declarations import LazyAttribute

import pcapi.core.bookings.factories as bookings_factories
import pcapi.core.offerers.factories as offerers_factories
import pcapi.core.payments.factories as payments_factories
from pcapi.core.testing import BaseFactory
from pcapi.domain import reimbursement

from . import models


class BusinessUnitFactory(BaseFactory):
    class Meta:
        model = models.BusinessUnit

    name = factory.Sequence("Business unit #{}".format)
    siret = factory.Sequence("{:014}".format)
    status = models.BusinessUnitStatus.ACTIVE

    bankAccount = factory.SubFactory("pcapi.core.offers.factories.BankInformationFactory")


class BusinessUnitVenueLinkFactory(BaseFactory):
    class Meta:
        model = models.BusinessUnitVenueLink

    businessUnit = factory.SelfAttribute("venue.businessUnit")
    venue = factory.SubFactory(offerers_factories.VenueFactory)
    timespan = factory.LazyFunction(
        lambda: [
            datetime.datetime.utcnow() - datetime.timedelta(days=365),
            None,
        ]
    )


class PricingFactory(BaseFactory):
    class Meta:
        model = models.Pricing

    status = models.PricingStatus.VALIDATED
    booking = factory.SubFactory(bookings_factories.UsedIndividualBookingFactory)
    businessUnit = factory.SelfAttribute("booking.venue.businessUnit")
    siret = factory.SelfAttribute("booking.venue.siret")
    valueDate = factory.SelfAttribute("booking.dateUsed")
    amount = LazyAttribute(lambda pricing: -int(100 * pricing.booking.total_amount))
    standardRule = "Remboursement total pour les offres physiques"
    revenue = LazyAttribute(lambda pricing: int(100 * pricing.booking.total_amount))


class EducationalPricingFactory(BaseFactory):
    class Meta:
        model = models.Pricing

    status = models.PricingStatus.VALIDATED
    booking = factory.SubFactory(bookings_factories.UsedEducationalBookingFactory)
    businessUnit = factory.SelfAttribute("booking.venue.businessUnit")
    siret = factory.SelfAttribute("booking.venue.siret")
    valueDate = factory.SelfAttribute("booking.dateUsed")
    amount = LazyAttribute(lambda pricing: -int(100 * pricing.booking.total_amount))
    revenue = LazyAttribute(lambda pricing: int(100 * pricing.booking.total_amount))
    standardRule = "Remboursement total"


class PricingLineFactory(BaseFactory):
    class Meta:
        model = models.PricingLine

    pricing = factory.SubFactory(PricingFactory)
    amount = LazyAttribute(lambda line: -line.pricing.amount)
    category = models.PricingLineCategory.OFFERER_REVENUE


class PricingLogFactory(BaseFactory):
    class Meta:
        model = models.PricingLog

    pricing = factory.SubFactory(PricingFactory)
    statusBefore = models.PricingStatus.VALIDATED
    statusAfter = models.PricingStatus.CANCELLED
    reason = models.PricingLogReason.MARK_AS_UNUSED


class InvoiceFactory(BaseFactory):
    class Meta:
        model = models.Invoice

    businessUnit = factory.SubFactory(BusinessUnitFactory)
    amount = 1000
    reference = factory.Sequence("{:09}".format)
    token = factory.LazyFunction(secrets.token_urlsafe)


class CashflowBatchFactory(BaseFactory):
    class Meta:
        model = models.CashflowBatch

    cutoff = factory.LazyFunction(datetime.datetime.utcnow)


class CashflowFactory(BaseFactory):
    class Meta:
        model = models.Cashflow

    batch = factory.SubFactory(CashflowBatchFactory)
    status = models.CashflowStatus.ACCEPTED
    bankAccount = factory.SelfAttribute("businessUnit.bankAccount")


class CashflowPricingFactory(BaseFactory):
    class Meta:
        model = models.CashflowPricing

    cashflow = factory.SubFactory(CashflowFactory)
    pricing = factory.SubFactory(PricingFactory, businessUnit=factory.SelfAttribute("..cashflow.businessUnit"))


# Factories below are deprecated and should probably NOT BE USED in
# any new test. See comment in `models.py` above the definition of the
# `Payment` model.
REIMBURSEMENT_RULE_DESCRIPTIONS = {t.description for t in reimbursement.REGULAR_RULES}


class PaymentFactory(BaseFactory):
    class Meta:
        model = models.Payment

    author = "batch"
    booking = factory.SubFactory(bookings_factories.UsedIndividualBookingFactory)
    amount = factory.LazyAttribute(
        lambda payment: payment.booking.total_amount * decimal.Decimal(payment.reimbursementRate)
    )
    recipientSiren = factory.SelfAttribute("booking.stock.offer.venue.managingOfferer.siren")
    reimbursementRule = factory.Iterator(REIMBURSEMENT_RULE_DESCRIPTIONS)
    reimbursementRate = factory.LazyAttribute(
        lambda payment: reimbursement.get_reimbursement_rule(  # type: ignore [attr-defined]
            payment.booking, reimbursement.CustomRuleFinder(), decimal.Decimal(0)
        ).rate
    )
    recipientName = "Récipiendaire"
    iban = "CF13QSDFGH456789"
    bic = "QSDFGH8Z555"
    transactionLabel = None

    @factory.post_generation
    def statuses(obj, create, extracted, **kwargs):  # type: ignore [no-untyped-def] # pylint: disable=no-self-argument

        if not create:
            return None
        if extracted is not None:
            return extracted
        status = PaymentStatusFactory(payment=obj, status=models.TransactionStatus.PENDING)
        return [status]


class PaymentStatusFactory(BaseFactory):
    class Meta:
        model = models.PaymentStatus

    payment = factory.SubFactory(PaymentFactory, statuses=[])


class PaymentWithCustomRuleFactory(PaymentFactory):
    amount = factory.LazyAttribute(lambda payment: payment.customReimbursementRule.amount)
    customReimbursementRule = factory.SubFactory(payments_factories.CustomReimbursementRuleFactory)
    reimbursementRule = None
    reimbursementRate = None
