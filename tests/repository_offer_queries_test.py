from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time

from models import Thing, PcObject, Event
from models.offer_type import EventType, ThingType
from repository.offer_queries import department_or_national_offers, \
    find_activation_offers, \
    find_offers_with_filter_parameters, \
    get_offers_for_recommendations_search, \
    get_active_offers_by_type
from tests.conftest import clean_database
from utils.test_utils import create_booking, \
    create_event, \
    create_event_occurrence, \
    create_event_offer, \
    create_mediation, \
    create_stock_from_event_occurrence, \
    create_thing, \
    create_thing_offer, \
    create_offerer, \
    create_stock_from_offer, \
    create_stock_with_thing_offer, \
    create_user_offerer, \
    create_user, \
    create_venue

REFERENCE_DATE = '2017-10-15 09:21:34'


@pytest.mark.standalone
class DepartmentOrNationalOffersTest:
    @clean_database
    def test_returns_national_thing_with_different_department(self, app):
        # given
        thing = create_thing(thing_name='Lire un livre', is_national=True)
        offerer = create_offerer()
        venue = create_venue(offerer, postal_code='34000', departement_code='34')
        offer = create_thing_offer(venue, thing)
        PcObject.check_and_save(offer)
        query = Thing.query.filter_by(name='Lire un livre')

        # when
        query = department_or_national_offers(query, Thing, ['93'])

        # then
        assert thing in query.all()

    @clean_database
    def test_returns_national_event_with_different_department(self, app):
        # given
        event = create_event('Voir une pièce', is_national=True)
        offerer = create_offerer()
        venue = create_venue(offerer, is_virtual=False, postal_code='29000', departement_code='29')
        offer = create_event_offer(venue, event)
        PcObject.check_and_save(offer)
        query = Event.query.filter_by(name='Voir une pièce')

        # when
        query = department_or_national_offers(query, Event, ['93'])

        # then
        assert event in query.all()

    @clean_database
    def test_returns_nothing_if_event_is_not_in_given_department_list(self, app):
        # given
        event = create_event('Voir une pièce', is_national=False)
        offerer = create_offerer()
        venue = create_venue(offerer, is_virtual=False, postal_code='29000', departement_code='29')
        offer = create_event_offer(venue, event)
        PcObject.check_and_save(offer)
        query = Event.query.filter_by(name='Voir une pièce')

        # when
        query = department_or_national_offers(query, Event, ['34'])

        # then
        assert query.count() == 0

    @clean_database
    def test_returns_an_event_regardless_of_department_if_department_list_contains_00(self, app):
        # given
        event = create_event('Voir une pièce', is_national=False)
        offerer = create_offerer()
        venue = create_venue(offerer, is_virtual=False, postal_code='29000', departement_code='29')
        offer = create_event_offer(venue, event)
        PcObject.check_and_save(offer)
        query = Event.query.filter_by(name='Voir une pièce')

        # when
        query = department_or_national_offers(query, Event, ['00'])

        # then
        assert query.count() == 1

    @clean_database
    def test_returns_an_event_if_it_is_given_in_department_list(self, app):
        # given
        event = create_event('Voir une pièce', is_national=False)
        offerer = create_offerer()
        venue = create_venue(offerer, is_virtual=False, postal_code='29000', departement_code='29')
        offer = create_event_offer(venue, event)
        PcObject.check_and_save(offer)
        query = Event.query.filter_by(name='Voir une pièce')

        # when
        query = department_or_national_offers(query, Event, ['29'])

        # then
        assert query.count() == 1


@freeze_time(REFERENCE_DATE)
@pytest.mark.standalone
class GetOffersForRecommendationsSearchTest:
    @clean_database
    def test_search_by_one_event_type_returns_only_offers_on_events_of_that_type(self, app):
        # Given
        type_label = EventType.CONFERENCE_DEBAT_DEDICACE
        other_type_label = EventType.MUSIQUE

        conference_event1 = create_event('Rencontre avec Franck Lepage', event_type=type_label)
        conference_event2 = create_event('Conférence ouverte', event_type=type_label)
        concert_event = create_event('Concert de Gael Faye', event_type=other_type_label)

        offerer = create_offerer(
            siren='507633576',
            address='1 BD POISSONNIERE',
            city='Paris',
            postal_code='75002',
            name='LE GRAND REX PARIS',
            validation_token=None,
            iban=None,
            bic=None
        )
        venue = create_venue(
            offerer,
            name='LE GRAND REX PARIS',
            address="1 BD POISSONNIERE",
            postal_code='75002',
            city="Paris",
            departement_code='75',
            is_virtual=False,
            longitude="2.4002701",
            latitude="48.8363788",
            siret="50763357600016"
        )

        conference_offer1 = create_event_offer(venue, conference_event1)
        conference_offer2 = create_event_offer(venue, conference_event2)
        concert_offer = create_event_offer(venue, concert_event)

        conference_event_occurrence1 = create_event_occurrence(conference_offer1)
        conference_event_occurrence2 = create_event_occurrence(conference_offer2)
        concert_event_occurrence = create_event_occurrence(concert_offer)

        conference_stock1 = create_stock_from_event_occurrence(conference_event_occurrence1)
        conference_stock2 = create_stock_from_event_occurrence(conference_event_occurrence2)
        concert_stock = create_stock_from_event_occurrence(concert_event_occurrence)

        PcObject.check_and_save(conference_stock1, conference_stock2, concert_stock)

        # When
        offers = get_offers_for_recommendations_search(
            type_values=[
                str(type_label)
            ],
        )

        # Then
        assert conference_offer1 in offers
        assert conference_offer2 in offers
        assert concert_offer not in offers

    @clean_database
    def test_search_by_one_thing_type_returns_only_offers_on_things_of_that_type(self, app):
        # Given
        type_label_ok = ThingType.JEUX_VIDEO
        type_label_ko = ThingType.LIVRE_EDITION

        thing_ok1 = create_thing(thing_type=type_label_ok)
        thing_ok2 = create_thing(thing_type=type_label_ok)
        thing_ko = create_thing(thing_type=type_label_ko)
        event_ko = create_event(event_type=EventType.CINEMA)

        offerer = create_offerer()
        venue = create_venue(offerer)

        ok_offer_1 = create_thing_offer(venue, thing_ok1)
        ok_offer_2 = create_thing_offer(venue, thing_ok2)
        ko_offer = create_thing_offer(venue, thing_ko)
        ko_event_offer = create_event_offer(venue, event_ko)

        ko_event_occurrence = create_event_occurrence(ko_event_offer)

        ok_stock1 = create_stock_from_offer(ok_offer_1)
        ok_stock2 = create_stock_from_offer(ok_offer_2)
        ko_stock1 = create_stock_from_offer(ko_offer)
        ko_stock2 = create_stock_from_event_occurrence(ko_event_occurrence)

        PcObject.check_and_save(ok_stock1, ok_stock2, ko_stock1, ko_stock2)

        # When
        offers = get_offers_for_recommendations_search(
            type_values=[
                str(type_label_ok)
            ],
        )

        # Then
        assert len(offers) == 2
        assert ok_offer_1 in offers
        assert ok_offer_2 in offers

    @clean_database
    def test_search_by_datetime_only_returns_recommendations_starting_during_time_interval(self, app):
        # Duplicate
        # Given
        offerer = create_offerer()
        venue = create_venue(offerer)

        ok_stock = _create_event_stock_and_offer_for_date(venue, datetime(2018, 1, 6, 12, 30))
        ko_stock_before = _create_event_stock_and_offer_for_date(venue, datetime(2018, 1, 1, 12, 30))
        ko_stock_after = _create_event_stock_and_offer_for_date(venue, datetime(2018, 1, 10, 12, 30))
        ok_stock_thing = create_stock_with_thing_offer(offerer, venue, None)

        PcObject.check_and_save(ok_stock, ko_stock_before, ko_stock_after)

        # When
        search_result_offers = get_offers_for_recommendations_search(
            days_intervals=[
                [datetime(2018, 1, 6, 12, 0), datetime(2018, 1, 6, 13, 0)]
            ],
        )

        # Then
        assert ok_stock.resolvedOffer in search_result_offers
        assert ok_stock_thing.resolvedOffer in search_result_offers
        assert ko_stock_before.resolvedOffer not in search_result_offers
        assert ko_stock_after.resolvedOffer not in search_result_offers

    @clean_database
    def test_search_with_several_partial_keywords_returns_things_and_events_with_name_containing_keywords(self, app):
        # Given
        thing_ok = create_thing(thing_name='Rencontre de michel')
        thing = create_thing(thing_name='Rencontre avec jean-luc')
        event = create_event(event_name='Rencontre avec jean-mimi chelou')
        offerer = create_offerer()
        venue = create_venue(offerer)
        thing_ok_offer = create_thing_offer(venue, thing_ok)
        thing_ko_offer = create_thing_offer(venue, thing)
        event_ko_offer = create_event_offer(venue, event)
        event_ko_occurrence = create_event_occurrence(event_ko_offer)
        event_ko_stock = create_stock_from_event_occurrence(event_ko_occurrence)
        thing_ok_stock = create_stock_from_offer(thing_ok_offer)
        thing_ko_stock = create_stock_from_offer(thing_ko_offer)
        PcObject.check_and_save(event_ko_stock, thing_ok_stock, thing_ko_stock)

        # When
        offers = get_offers_for_recommendations_search(keywords_string='renc michel')

        # Then
        assert thing_ok_offer in offers
        assert thing_ko_offer not in offers
        assert event_ko_offer not in offers

    @clean_database
    def test_search_without_accents_matches_offer_with_accents_1(self, app):
        # Given
        thing_ok = create_thing(thing_name='Nez à nez')
        offerer = create_offerer()
        venue = create_venue(offerer)
        thing_ok_offer = create_thing_offer(venue, thing_ok)
        thing_ok_stock = create_stock_from_offer(thing_ok_offer)
        PcObject.check_and_save(thing_ok_stock)

        # When
        offers = get_offers_for_recommendations_search(keywords_string='nez a')

        # Then
        assert thing_ok_offer in offers

    @clean_database
    def test_search_with_accents_matches_offer_without_accents_2(self, app):
        # Given
        thing_ok = create_thing(thing_name='Déjà')
        offerer = create_offerer()
        venue = create_venue(offerer)
        thing_ok_offer = create_thing_offer(venue, thing_ok)
        thing_ok_stock = create_stock_from_offer(thing_ok_offer)
        PcObject.check_and_save(thing_ok_stock)

        # When
        offers = get_offers_for_recommendations_search(keywords_string='deja')

        #
        assert thing_ok_offer in offers

    @clean_database
    def test_search_does_not_return_offers_by_types_with_booking_limit_date_over(self, app):
        # Given
        three_hours_ago = datetime.utcnow() - timedelta(hours=3)
        type_label = ThingType.JEUX_VIDEO
        offerer = create_offerer()
        venue = create_venue(offerer)
        offer = create_thing_offer(venue, thing_type=type_label)
        outdated_stock = create_stock_from_offer(offer, booking_limit_datetime=three_hours_ago)

        PcObject.check_and_save(outdated_stock)

        # When
        search_result_offers = get_offers_for_recommendations_search(type_values=[
            str(type_label)
        ], )

        # Then
        assert not search_result_offers

    @clean_database
    def test_search_does_not_return_offers_by_types_with_all_beginning_datetime_passed_and_no_booking_limit_datetime(
            self, app):
        # Given
        three_hours_ago = datetime.utcnow() - timedelta(hours=3)
        type_label = EventType.MUSEES_PATRIMOINE
        offerer = create_offerer()
        venue = create_venue(offerer)
        offer = create_event_offer(venue, event_type=type_label)
        outdated_event_occurrence = create_event_occurrence(offer, beginning_datetime=three_hours_ago,
                                                            end_datetime=datetime.utcnow())
        stock = create_stock_from_event_occurrence(outdated_event_occurrence, booking_limit_date=None)

        PcObject.check_and_save(stock, outdated_event_occurrence)

        # When
        search_result_offers = get_offers_for_recommendations_search(type_values=[
            str(type_label)
        ], )

        # Then
        assert not search_result_offers

    @clean_database
    def test_search_return_offers_by_types_with_some_but_not_all_beginning_datetime_passed_and_no_booking_limit_datetime(
            self, app):
        # Given
        three_hours_ago = datetime.utcnow() - timedelta(hours=3)
        in_three_hours = datetime.utcnow() + timedelta(hours=3)
        in_four_hours = datetime.utcnow() + timedelta(hours=4)
        type_label = EventType.MUSEES_PATRIMOINE
        offerer = create_offerer()
        venue = create_venue(offerer)
        offer = create_event_offer(venue, event_type=type_label)
        outdated_event_occurrence = create_event_occurrence(offer, beginning_datetime=three_hours_ago,
                                                            end_datetime=datetime.utcnow())
        future_event_occurrence = create_event_occurrence(offer, beginning_datetime=in_three_hours,
                                                          end_datetime=in_four_hours)
        stock = create_stock_from_event_occurrence(future_event_occurrence, booking_limit_date=None)

        PcObject.check_and_save(stock, future_event_occurrence, outdated_event_occurrence)

        # When
        search_result_offers = get_offers_for_recommendations_search(type_values=[
            str(type_label)
        ], )

        # Then
        assert offer in search_result_offers


@clean_database
@pytest.mark.standalone
def test_get_active_offers_by_type_when_departement_code_00(app):
    # Given
    offerer = create_offerer()
    venue_34 = create_venue(offerer, postal_code='34000', departement_code='34', siret=offerer.siren + '11111')
    venue_93 = create_venue(offerer, postal_code='93000', departement_code='93', siret=offerer.siren + '22222')
    venue_75 = create_venue(offerer, postal_code='75000', departement_code='75', siret=offerer.siren + '33333')
    offer_34 = create_thing_offer(venue_34)
    offer_93 = create_thing_offer(venue_93)
    offer_75 = create_thing_offer(venue_75)
    stock_34 = create_stock_from_offer(offer_34)
    stock_93 = create_stock_from_offer(offer_93)
    stock_75 = create_stock_from_offer(offer_75)
    user = create_user(departement_code='00')

    PcObject.check_and_save(user, stock_34, stock_93, stock_75)

    # When
    offers = get_active_offers_by_type(Thing, user=user, department_codes=['00'], offer_id=None)

    # Then
    assert offer_34 in offers
    assert offer_93 in offers
    assert offer_75 in offers


@clean_database
@pytest.mark.standalone
def test_get_active_event_offers_only_returns_event_offers(app):
    # Given
    user = create_user(departement_code='93')
    offerer = create_offerer()
    venue = create_venue(offerer, departement_code='93')
    offer1 = create_thing_offer(venue, thumb_count=1)
    offer2 = create_event_offer(venue, thumb_count=1)
    now = datetime.utcnow()
    event_occurrence = create_event_occurrence(offer2, beginning_datetime=now + timedelta(hours=72),
                                               end_datetime=now + timedelta(hours=74))
    mediation = create_mediation(offer2)
    stock1 = create_stock_from_offer(offer1, price=0)
    stock2 = create_stock_from_event_occurrence(event_occurrence, price=0, available=10,
                                                booking_limit_date=now + timedelta(days=2))
    PcObject.check_and_save(user, stock1, stock2, mediation, event_occurrence)

    # When
    offers = get_active_offers_by_type(Event, user=user, department_codes=['93'])
    # Then
    assert len(offers) == 1
    assert offers[0].id == offer2.id


@clean_database
@pytest.mark.standalone
def test_find_activation_offers_returns_activation_offers_in_given_departement(app):
    # given
    offerer = create_offerer()
    venue1 = create_venue(offerer, siret=offerer.siren + '12345', postal_code='34000', departement_code='34')
    venue2 = create_venue(offerer, siret=offerer.siren + '54321', postal_code='93000', departement_code='93')
    offer1 = create_event_offer(venue1, event_type=EventType.ACTIVATION)
    offer2 = create_event_offer(venue1, event_type=EventType.SPECTACLE_VIVANT)
    offer3 = create_event_offer(venue2, event_type=EventType.ACTIVATION)
    stock1 = create_stock_from_offer(offer1)
    stock2 = create_stock_from_offer(offer2)
    stock3 = create_stock_from_offer(offer3)
    PcObject.check_and_save(stock1, stock2, stock3)

    # when
    offers = find_activation_offers('34').all()

    # then
    assert len(offers) == 1


@clean_database
@pytest.mark.standalone
def test_find_activation_offers_returns_activation_offers_if_offer_is_national(app):
    # given
    offerer = create_offerer()
    venue1 = create_venue(offerer, siret=offerer.siren + '12345', postal_code='34000', departement_code='34')
    venue2 = create_venue(offerer, siret=offerer.siren + '54321', postal_code='93000', departement_code='93')
    offer1 = create_event_offer(venue1, event_type=EventType.ACTIVATION)
    offer2 = create_thing_offer(venue1, thing_type=ThingType.AUDIOVISUEL)
    offer3 = create_event_offer(venue2, event_type=EventType.ACTIVATION, is_national=True)
    offer4 = create_event_offer(venue2, event_type=EventType.ACTIVATION, is_national=True)
    stock1 = create_stock_from_offer(offer1)
    stock2 = create_stock_from_offer(offer2)
    stock3 = create_stock_from_offer(offer3)
    stock4 = create_stock_from_offer(offer4)
    PcObject.check_and_save(stock1, stock2, stock3, stock4)

    # when
    offers = find_activation_offers('34').all()

    # then
    assert len(offers) == 3


@clean_database
@pytest.mark.standalone
def test_find_activation_offers_returns_activation_offers_in_all_ile_de_france_if_departement_is_93(app):
    # given
    offerer = create_offerer()
    venue1 = create_venue(offerer, siret=offerer.siren + '12345', postal_code='34000', departement_code='34')
    venue2 = create_venue(offerer, siret=offerer.siren + '67890', postal_code='75000', departement_code='75')
    venue3 = create_venue(offerer, siret=offerer.siren + '54321', postal_code='78000', departement_code='78')
    offer1 = create_event_offer(venue1, event_type=EventType.ACTIVATION)
    offer2 = create_event_offer(venue2, event_type=EventType.ACTIVATION)
    offer3 = create_event_offer(venue3, event_type=EventType.ACTIVATION)
    stock1 = create_stock_from_offer(offer1)
    stock2 = create_stock_from_offer(offer2)
    stock3 = create_stock_from_offer(offer3)
    PcObject.check_and_save(stock1, stock2, stock3)

    # when
    offers = find_activation_offers('93').all()

    # then
    assert len(offers) == 2


@clean_database
@pytest.mark.standalone
def test_find_activation_offers_returns_activation_offers_with_available_stocks(app):
    # given
    offerer = create_offerer()
    venue1 = create_venue(offerer, siret=offerer.siren + '12345', postal_code='93000', departement_code='93')
    venue2 = create_venue(offerer, siret=offerer.siren + '67890', postal_code='93000', departement_code='93')
    venue3 = create_venue(offerer, siret=offerer.siren + '54321', postal_code='93000', departement_code='93')
    offer1 = create_event_offer(venue1, event_type=EventType.ACTIVATION)
    offer2 = create_event_offer(venue2, event_type=EventType.ACTIVATION)
    offer3 = create_event_offer(venue3, event_type=EventType.ACTIVATION)
    offer4 = create_event_offer(venue3, event_type=EventType.ACTIVATION)
    stock1 = create_stock_from_offer(offer1, price=0, available=0)
    stock2 = create_stock_from_offer(offer2, price=0, available=10)
    stock3 = create_stock_from_offer(offer3, price=0, available=1)
    booking = create_booking(create_user(), stock3, venue=venue3, quantity=1)
    PcObject.check_and_save(stock1, stock2, stock3, booking, offer4)

    # when
    offers = find_activation_offers('93').all()

    # then
    assert len(offers) == 1


@clean_database
@pytest.mark.standalone
def test_find_activation_offers_returns_activation_offers_with_future_booking_limit_datetime(app):
    # given
    now = datetime.utcnow()
    five_days_ago = now - timedelta(days=5)
    next_week = now + timedelta(days=7)
    offerer = create_offerer()
    venue1 = create_venue(offerer, siret=offerer.siren + '12345', postal_code='93000', departement_code='93')
    venue2 = create_venue(offerer, siret=offerer.siren + '67890', postal_code='93000', departement_code='93')
    venue3 = create_venue(offerer, siret=offerer.siren + '54321', postal_code='93000', departement_code='93')
    offer1 = create_event_offer(venue1, event_type=EventType.ACTIVATION)
    offer2 = create_event_offer(venue2, event_type=EventType.ACTIVATION)
    offer3 = create_event_offer(venue3, event_type=EventType.ACTIVATION)
    stock1 = create_stock_from_offer(offer1, price=0, booking_limit_datetime=five_days_ago)
    stock2 = create_stock_from_offer(offer2, price=0, booking_limit_datetime=next_week)
    stock3 = create_stock_from_offer(offer3, price=0, booking_limit_datetime=None)
    PcObject.check_and_save(stock1, stock2, stock3)

    # when
    offers = find_activation_offers('93').all()

    # then
    assert len(offers) == 2


@clean_database
@pytest.mark.standalone
def test_find_offers_with_filter_parameters_with_partial_keywords_and_filter_by_venue(app):
    user = create_user(email='offerer@email.com')
    offerer1 = create_offerer(siren='123456789')
    offerer2 = create_offerer(siren='987654321')
    ko_offerer3 = create_offerer(siren='123456780')
    user_offerer1 = create_user_offerer(user, offerer1)
    user_offerer2 = create_user_offerer(user, offerer2)

    ok_event1 = create_event(event_name='Rencontre avec Jacques Martin')
    ok_thing = create_thing(thing_name='Rencontrez Jacques Chirac')
    event2 = create_event(event_name='Concert de contrebasse')
    thing1 = create_thing(thing_name='Jacques la fripouille')
    thing2 = create_thing(thing_name='Belle du Seigneur')
    offerer = create_offerer()
    venue1 = create_venue(offerer1, name='Bataclan', city='Paris', siret=offerer.siren + '12345')
    venue2 = create_venue(offerer2, name='Librairie la Rencontre', city='Saint Denis', siret=offerer.siren + '54321')
    ko_venue3 = create_venue(ko_offerer3, name='Une librairie du méchant concurrent gripsou', city='Saint Denis',
                             siret=ko_offerer3.siren + '54321')
    ok_offer1 = create_event_offer(venue1, ok_event1)
    ok_offer2 = create_thing_offer(venue1, ok_thing)
    ko_offer2 = create_event_offer(venue1, event2)
    ko_offer3 = create_thing_offer(ko_venue3, thing1)
    ko_offer4 = create_thing_offer(venue2, thing2)
    PcObject.check_and_save(
        user_offerer1, user_offerer2, ko_offerer3,
        ok_offer1, ko_offer2, ko_offer3, ko_offer4
    )

    # when
    offers = find_offers_with_filter_parameters(
        user,
        venue_id=venue1.id,
        keywords_string='Jacq Rencon'
    ).all()

    # then
    offers_id = [offer.id for offer in offers]
    assert ok_offer1.id in offers_id
    assert ok_offer2.id in offers_id
    assert ko_offer2.id not in offers_id
    assert ko_offer3.id not in offers_id
    assert ko_offer4.id not in offers_id


@clean_database
@pytest.mark.standalone
def test_get_active_offers_should_not_return_activation_event(app):
    # Given
    offerer = create_offerer()
    venue_93 = create_venue(offerer, postal_code='93000', departement_code='93', siret=offerer.siren + '33333')
    offer_93 = create_event_offer(venue_93)
    offer_activation_93 = create_event_offer(venue_93, event_type=EventType.ACTIVATION)
    event_occurrence_93 = create_event_occurrence(offer_93)
    event_occurrence_activation_93 = create_event_occurrence(offer_activation_93)
    stock_93 = create_stock_from_event_occurrence(event_occurrence_93)
    stock_activation_93 = create_stock_from_event_occurrence(event_occurrence_activation_93)
    user = create_user(departement_code='00')

    PcObject.check_and_save(user, stock_93, stock_activation_93)

    # When
    offers = get_active_offers_by_type(Event, user=user, department_codes=['00'], offer_id=None)

    # Then
    assert offer_93 in offers
    assert offer_activation_93 not in offers


@clean_database
@pytest.mark.standalone
def test_get_active_offers_should_not_return_activation_thing(app):
    # Given
    offerer = create_offerer()
    venue_93 = create_venue(offerer, postal_code='93000', departement_code='93', siret=offerer.siren + '33333')
    thing_93 = create_thing_offer(venue_93)
    thing_activation_93 = create_thing_offer(venue_93, thing_type=ThingType.ACTIVATION)
    stock_93 = create_stock_from_offer(thing_93)
    stock_activation_93 = create_stock_from_offer(thing_activation_93)
    user = create_user(departement_code='00')

    PcObject.check_and_save(user, stock_93, stock_activation_93)

    # When
    offers = get_active_offers_by_type(Thing, user=user, department_codes=['00'], offer_id=None)

    # Then
    assert thing_93 in offers
    assert thing_activation_93 not in offers


def _create_event_stock_and_offer_for_date(venue, date):
    event = create_event()
    offer = create_event_offer(venue, event)
    event_occurrence = create_event_occurrence(offer, beginning_datetime=date, end_datetime=date + timedelta(hours=1))
    stock = create_stock_from_event_occurrence(event_occurrence, booking_limit_date=date)
    return stock
