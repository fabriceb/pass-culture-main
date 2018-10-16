from abc import ABC, abstractmethod
from decimal import Decimal
from enum import Enum

from models import Booking


class ReimbursementRule(ABC):
    def is_active(self):
        return True

    @abstractmethod
    def is_relevant(self, booking, **kwargs):
        pass

    @property
    @abstractmethod
    def rate(self):
        pass

    @property
    @abstractmethod
    def valid_from(self):
        pass

    @property
    @abstractmethod
    def valid_until(self):
        pass

    @property
    @abstractmethod
    def description(self):
        pass

    def apply(self, booking: Booking):
        return Decimal(booking.value * self.rate)


class DigitalThingsReimbursement(ReimbursementRule):
    rate = Decimal(0)
    description = 'Pas de remboursement pour les offres digitales'
    valid_from = None
    valid_until = None

    def is_relevant(self, booking, **kwargs):
        return booking.stock.resolvedOffer.eventOrThing.isDigital


class PhysicalOffersReimbursement(ReimbursementRule):
    rate = Decimal(1)
    description = 'Remboursement total pour les offres physiques'
    valid_from = None
    valid_until = None

    def is_relevant(self, booking, **kwargs):
        return not booking.stock.resolvedOffer.eventOrThing.isDigital


class MaxReimbursementByOfferer(ReimbursementRule):
    rate = Decimal(0)
    description = 'Pas de remboursement au dessus du plafond de 23 000 € par offreur'
    valid_from = None
    valid_until = None

    def is_relevant(self, booking, **kwargs):
        if booking.stock.resolvedOffer.eventOrThing.isDigital:
            return False
        else:
            return kwargs['cumulative_value'] > 23000


class ReimbursementRules(Enum):
    DIGITAL_THINGS = DigitalThingsReimbursement()
    PHYSICAL_OFFERS = PhysicalOffersReimbursement()
    MAX_REIMBURSEMENT = MaxReimbursementByOfferer()


class BookingReimbursement:
    def __init__(self, booking: Booking, reimbursement: ReimbursementRules, reimbursed_amount: Decimal):
        self.booking = booking
        self.reimbursement = reimbursement
        self.reimbursed_amount = reimbursed_amount

    def as_dict(self, include=None):
        dict_booking = self.booking._asdict(include=include)
        dict_booking['token'] = dict_booking['token'] if dict_booking['isUsed'] else None
        dict_booking['reimbursed_amount'] = self.reimbursed_amount
        dict_booking['reimbursement_rule'] = self.reimbursement.value.description
        return dict_booking


def find_all_booking_reimbursement(bookings):
    reimbursements = []
    cumulative_bookings_value = 0

    for booking in bookings:
        if ReimbursementRules.PHYSICAL_OFFERS.value.is_relevant(booking):
            cumulative_bookings_value = cumulative_bookings_value + booking.value

        potential_rules = _find_potential_rules(booking, cumulative_bookings_value)
        elected_rule = min(potential_rules, key=lambda x: x['amount'])
        reimbursements.append(BookingReimbursement(booking, elected_rule['rule'], elected_rule['amount']))

    return reimbursements


def _find_potential_rules(booking, cumulative_bookings_value):
    relevant_rules = []
    for rule in ReimbursementRules:
        if rule.value.is_active and rule.value.is_relevant(booking, cumulative_value=cumulative_bookings_value):
            reimbursed_amount = rule.value.apply(booking)
            relevant_rules.append({'rule': rule, 'amount': reimbursed_amount})
    return relevant_rules
