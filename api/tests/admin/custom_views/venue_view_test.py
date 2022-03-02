import re
from unittest.mock import patch

import pytest

from pcapi.admin.custom_views.venue_view import _get_venue_provider_link
from pcapi.core.bookings.factories import BookingFactory
from pcapi.core.bookings.models import BookingStatus
from pcapi.core.finance import factories as finance_factories
from pcapi.core.offerers.models import Venue
from pcapi.core.offers import factories as offers_factories
from pcapi.core.offers import models as offers_models
from pcapi.core.providers import factories as providers_factories
from pcapi.core.users import testing as sendinblue_testing
from pcapi.core.users.factories import AdminFactory
from pcapi.models import db

from tests.conftest import TestClient
from tests.conftest import clean_database


class VenueViewTest:
    @clean_database
    @patch("wtforms.csrf.session.SessionCSRF.validate_csrf_token")
    @patch("pcapi.core.search.async_index_offers_of_venue_ids")
    def test_update_venue_with_siret_not_attributed_to_a_business_unit(
        self, mocked_async_index_offers_of_venue_ids, mocked_validate_csrf_token, app
    ):
        AdminFactory(email="user@example.com")
        business_unit = finance_factories.BusinessUnitFactory(siret="11111111111111")
        venue = offers_factories.VenueFactory(siret="22222222222222", businessUnit=business_unit)
        id_at_provider = "11111"
        old_id_at_providers = f"{id_at_provider}@{venue.siret}"
        stock = offers_factories.StockFactory(
            offer__venue=venue, idAtProviders=old_id_at_providers, offer__idAtProvider=id_at_provider
        )

        data = dict(
            name=venue.name,
            siret="88888888888888",
            city=venue.city,
            postalCode=venue.postalCode,
            address=venue.address,
            publicName=venue.publicName,
            latitude=venue.latitude,
            longitude=venue.longitude,
            isPermanent=venue.isPermanent,
            isActive=venue.isActive,
        )

        client = TestClient(app.test_client()).with_session_auth("user@example.com")
        response = client.post(f"/pc/back-office/venue/edit/?id={venue.id}", form=data)

        assert response.status_code == 302

        venue_edited = Venue.query.get(venue.id)
        stock_edited = offers_models.Stock.query.get(stock.id)

        assert venue_edited.siret == "88888888888888"
        assert stock_edited.idAtProviders == "11111@88888888888888"
        assert venue.isActive

        mocked_async_index_offers_of_venue_ids.assert_not_called()

    @clean_database
    @patch("wtforms.csrf.session.SessionCSRF.validate_csrf_token")
    @patch("pcapi.core.search.async_index_offers_of_venue_ids")
    def test_cannot_update_venue_with_new_siret_already_attributed_to_a_business_unit(
        self, mocked_async_index_offers_of_venue_ids, mocked_validate_csrf_token, app
    ):
        AdminFactory(email="user@example.com")
        finance_factories.BusinessUnitFactory(siret="33333333333333", name="Superstore")
        venue = offers_factories.VenueFactory(siret="22222222222222")

        data = dict(
            name=venue.name,
            siret="33333333333333",
            city=venue.city,
            postalCode=venue.postalCode,
            address=venue.address,
            publicName=venue.publicName,
            latitude=venue.latitude,
            longitude=venue.longitude,
            isPermanent=venue.isPermanent,
        )
        client = TestClient(app.test_client()).with_session_auth("user@example.com")
        response = client.post(f"/pc/back-office/venue/edit/?id={venue.id}", form=data)

        assert response.status_code == 200
        content = response.data.decode(response.charset)
        assert (
            "Ce SIRET a déjà été attribué au point de remboursement Superstore,"
            " il ne peut pas être attribué à ce lieu" in content
        )
        venue_edited = Venue.query.get(venue.id)
        assert venue_edited.siret == "22222222222222"
        mocked_async_index_offers_of_venue_ids.assert_not_called()

    @clean_database
    @patch("wtforms.csrf.session.SessionCSRF.validate_csrf_token")
    @patch("pcapi.core.search.async_index_offers_of_venue_ids")
    def test_cannot_update_venue_with_siret_when_it_carries_a_business_unit(
        self, mocked_async_index_offers_of_venue_ids, mocked_validate_csrf_token, app
    ):
        AdminFactory(email="user@example.com")
        bu = finance_factories.BusinessUnitFactory(siret="22222222222222", name="Superstore")
        venue = offers_factories.VenueFactory(siret="22222222222222", businessUnit=bu)

        data = dict(
            name=venue.name,
            siret="33333333333333",
            city=venue.city,
            postalCode=venue.postalCode,
            address=venue.address,
            publicName=venue.publicName,
            latitude=venue.latitude,
            longitude=venue.longitude,
            isPermanent=venue.isPermanent,
        )
        client = TestClient(app.test_client()).with_session_auth("user@example.com")
        response = client.post(f"/pc/back-office/venue/edit/?id={venue.id}", form=data)

        assert response.status_code == 200
        content = response.data.decode(response.charset)
        assert (
            "Le SIRET de ce lieu est le SIRET de référence du point de remboursement Superstore, "
            "il ne peut pas être modifié." in content
        )
        venue_edited = Venue.query.get(venue.id)
        assert venue_edited.siret == "22222222222222"
        mocked_async_index_offers_of_venue_ids.assert_not_called()

    @clean_database
    @patch("wtforms.csrf.session.SessionCSRF.validate_csrf_token")
    def test_update_venue_other_offer_id_at_provider(self, mocked_validate_csrf_token, app):
        AdminFactory(email="user@example.com")
        business_unit = finance_factories.BusinessUnitFactory(siret="11111111111111")
        venue = offers_factories.VenueFactory(siret="22222222222222", businessUnit=business_unit)
        id_at_providers = "id_at_provider_ne_contenant_pas_le_siret"
        stock = offers_factories.StockFactory(
            offer__venue=venue, idAtProviders=id_at_providers, offer__idAtProvider=id_at_providers
        )

        data = dict(
            name=venue.name,
            siret="88888888888888",
            city=venue.city,
            postalCode=venue.postalCode,
            address=venue.address,
            publicName=venue.publicName,
            latitude=venue.latitude,
            longitude=venue.longitude,
            isPermanent=venue.isPermanent,
            isActive=venue.isActive,
        )

        client = TestClient(app.test_client()).with_session_auth("user@example.com")
        response = client.post(f"/pc/back-office/venue/edit/?id={venue.id}", form=data)

        assert response.status_code == 302

        venue_edited = Venue.query.get(venue.id)
        stock = offers_models.Stock.query.get(stock.id)
        offer = offers_models.Offer.query.get(stock.offer.id)

        assert venue_edited.siret == "88888888888888"
        assert stock.idAtProviders == "id_at_provider_ne_contenant_pas_le_siret"
        assert offer.idAtProvider == "id_at_provider_ne_contenant_pas_le_siret"

    @clean_database
    @patch("wtforms.csrf.session.SessionCSRF.validate_csrf_token")
    def test_update_venue_without_siret(self, mocked_validate_csrf_token, app):
        AdminFactory(email="user@example.com")
        business_unit = finance_factories.BusinessUnitFactory(siret="11111111111111")
        venue = offers_factories.VenueFactory(
            siret=None, comment="comment to allow null siret", businessUnit=business_unit
        )

        data = dict(
            name=venue.name,
            siret="88888888888888",
            city=venue.city,
            postalCode=venue.postalCode,
            address=venue.address,
            publicName=venue.publicName,
            latitude=venue.latitude,
            longitude=venue.longitude,
            isPermanent=venue.isPermanent,
            isActive=venue.isActive,
        )

        client = TestClient(app.test_client()).with_session_auth("user@example.com")
        response = client.post(f"/pc/back-office/venue/edit/?id={venue.id}", form=data)

        assert response.status_code == 302

    @clean_database
    @patch("wtforms.csrf.session.SessionCSRF.validate_csrf_token")
    @patch("pcapi.core.search.async_index_offers_of_venue_ids")
    def test_update_venue_reindex_all(self, mocked_async_index_offers_of_venue_ids, mocked_validate_csrf_token, app):
        AdminFactory(email="user@example.com")
        venue = offers_factories.VenueFactory(isPermanent=False)

        new_name = venue.name + "(updated)"
        data = dict(
            name=new_name,
            siret=venue.siret,
            city=venue.city,
            postalCode=venue.postalCode,
            address=venue.address,
            publicName=venue.publicName,
            latitude="42.01",
            longitude=venue.longitude,
            isPermanent=True,
            isActive=venue.isActive,
        )

        client = TestClient(app.test_client()).with_session_auth("user@example.com")
        response = client.post(f"/pc/back-office/venue/edit/?id={venue.id}", form=data)

        assert response.status_code == 302

        venue = Venue.query.get(venue.id)
        assert venue.isPermanent
        assert venue.name == new_name

        mocked_async_index_offers_of_venue_ids.assert_called_once_with([venue.id])

    @clean_database
    @patch("wtforms.csrf.session.SessionCSRF.validate_csrf_token")
    @patch("pcapi.core.search.async_index_offers_of_venue_ids")
    @patch("pcapi.core.search.async_index_venue_ids")
    def test_update_venue_reindex_venue_only(
        self, mocked_async_index_venue_ids, mocked_async_index_offers_of_venue_ids, mocked_validate_csrf_token, app
    ):
        AdminFactory(email="user@example.com")
        venue = offers_factories.VenueFactory(isPermanent=False)

        data = dict(
            name=venue.name,
            siret=venue.siret,
            city=venue.city,
            postalCode=venue.postalCode,
            address=venue.address,
            publicName=venue.publicName,
            latitude=venue.latitude,
            longitude=venue.longitude,
            isPermanent=True,
            isActive=venue.isActive,
        )

        client = TestClient(app.test_client()).with_session_auth("user@example.com")
        response = client.post(f"/pc/back-office/venue/edit/?id={venue.id}", form=data)

        assert response.status_code == 302

        venue = Venue.query.get(venue.id)
        assert venue.isPermanent

        mocked_async_index_venue_ids.assert_called_once_with([venue.id])
        mocked_async_index_offers_of_venue_ids.assert_not_called()

    @clean_database
    @patch("wtforms.csrf.session.SessionCSRF.validate_csrf_token")
    @patch("pcapi.core.search.async_index_offers_of_venue_ids")
    @patch("pcapi.core.search.async_index_venue_ids")
    @patch("pcapi.core.search.reindex_venue_ids")
    def test_reindex_when_tags_updated(
        self,
        mocked_reindex_venue_ids,
        mocked_async_index_venue_ids,
        mocked_async_index_offers_of_venue_ids,
        mocked_validate_csrf_token,
        client,
    ):
        admin = AdminFactory(email="user@example.com")
        venue = offers_factories.VenueFactory(isPermanent=True)
        tag = offers_factories.CriterionFactory()
        data = {
            "criteria": [tag.id],
            "name": venue.name,
            "siret": venue.siret,
            "city": venue.city,
            "postalCode": venue.postalCode,
            "address": venue.address,
            "publicName": venue.publicName,
            "latitude": venue.latitude,
            "longitude": venue.longitude,
            "isPermanent": True,
            "isActive": venue.isActive,
        }

        client = client.with_session_auth(admin.email)
        response = client.post(f"/pc/back-office/venue/edit/?id={venue.id}", form=data)

        assert response.status_code == 302

        mocked_reindex_venue_ids.assert_called_once_with([venue.id])
        mocked_async_index_venue_ids.assert_not_called()
        mocked_async_index_offers_of_venue_ids.assert_not_called()

    @pytest.mark.parametrize(
        "booking_status", [None, BookingStatus.USED, BookingStatus.CANCELLED, BookingStatus.REIMBURSED]
    )
    @clean_database
    @patch("wtforms.csrf.session.SessionCSRF.validate_csrf_token")
    def test_deactivate_venue(self, mocked_validate_csrf_token, client, booking_status):
        admin = AdminFactory(email="user@example.com")
        venue = offers_factories.VenueFactory()
        user_offerer = offers_factories.UserOffererFactory(offerer=venue.managingOfferer)
        if booking_status is not None:
            BookingFactory(stock__offer__venue=venue, status=booking_status)

        api_client = client.with_session_auth(admin.email)
        response = api_client.post(
            f"/pc/back-office/venue/edit/?id={venue.id}",
            form={
                "name": venue.name,
                "siret": venue.siret,
                "city": venue.city,
                "postalCode": venue.postalCode,
                "address": venue.address,
                "publicName": venue.publicName,
                "latitude": venue.latitude,
                "longitude": venue.longitude,
                "isPermanent": venue.isPermanent,
                # "isActive" is not sent in request when unchecked
            },
        )

        assert response.status_code == 302

        db.session.refresh(venue)
        assert not venue.isActive
        assert len(sendinblue_testing.sendinblue_requests) == 2
        assert {req["email"] for req in sendinblue_testing.sendinblue_requests} == {
            user_offerer.user.email,
            venue.bookingEmail,
        }

    @pytest.mark.parametrize("booking_status", [BookingStatus.PENDING, BookingStatus.CONFIRMED])
    @clean_database
    @patch("wtforms.csrf.session.SessionCSRF.validate_csrf_token")
    def test_deactivate_venue_rejected(self, mocked_validate_csrf_token, client, booking_status):
        admin = AdminFactory(email="user@example.com")
        venue = offers_factories.VenueFactory()
        offers_factories.UserOffererFactory(offerer=venue.managingOfferer)
        BookingFactory(stock__offer__venue=venue, status=booking_status)

        api_client = client.with_session_auth(admin.email)
        response = api_client.post(
            f"/pc/back-office/venue/edit/?id={venue.id}",
            form={
                "name": venue.name,
                "siret": venue.siret,
                "city": venue.city,
                "postalCode": venue.postalCode,
                "address": venue.address,
                "publicName": venue.publicName,
                "latitude": venue.latitude,
                "longitude": venue.longitude,
                "isPermanent": venue.isPermanent,
                # "isActive" is not sent in request when unchecked
            },
        )

        assert response.status_code == 200
        assert "Impossible de désactiver un lieu pour lequel des réservations sont en cours." in response.data.decode(
            "utf8"
        )

        db.session.refresh(venue)
        assert venue.isActive
        assert len(sendinblue_testing.sendinblue_requests) == 0

    @clean_database
    @patch("wtforms.csrf.session.SessionCSRF.validate_csrf_token")
    def test_reactivate_venue(self, mocked_validate_csrf_token, client):
        admin = AdminFactory(email="user@example.com")
        venue = offers_factories.VenueFactory(isActive=False)
        user_offerer = offers_factories.UserOffererFactory(offerer=venue.managingOfferer)

        api_client = client.with_session_auth(admin.email)
        response = api_client.post(
            f"/pc/back-office/venue/edit/?id={venue.id}",
            form={
                "name": venue.name,
                "siret": venue.siret,
                "city": venue.city,
                "postalCode": venue.postalCode,
                "address": venue.address,
                "publicName": venue.publicName,
                "latitude": venue.latitude,
                "longitude": venue.longitude,
                "isPermanent": venue.isPermanent,
                "isActive": "y",
            },
        )

        assert response.status_code == 302

        db.session.refresh(venue)
        assert venue.isActive
        assert len(sendinblue_testing.sendinblue_requests) == 2
        assert {req["email"] for req in sendinblue_testing.sendinblue_requests} == {
            user_offerer.user.email,
            venue.bookingEmail,
        }

    @clean_database
    @patch("wtforms.csrf.session.SessionCSRF.validate_csrf_token")
    def test_delete_venue(self, mocked_validate_csrf_token, client):
        admin = AdminFactory(email="user@example.com")
        venue = offers_factories.VenueFactory(bookingEmail="booking@example.com")
        user_offerer1 = offers_factories.UserOffererFactory(offerer=venue.managingOfferer)
        user_offerer2 = offers_factories.UserOffererFactory(offerer=venue.managingOfferer)

        api_client = client.with_session_auth(admin.email)
        response = api_client.post(
            "/pc/back-office/venue/delete/", form={"id": venue.id, "url": "/pc/back-office/venue/"}
        )

        assert response.status_code == 302
        assert len(Venue.query.all()) == 0
        assert len(sendinblue_testing.sendinblue_requests) == 3
        assert {req["email"] for req in sendinblue_testing.sendinblue_requests} == {
            user_offerer1.user.email,
            user_offerer2.user.email,
            "booking@example.com",
        }

    @pytest.mark.parametrize(
        "booking_status",
        [
            BookingStatus.PENDING,
            BookingStatus.USED,
            BookingStatus.CONFIRMED,
            BookingStatus.CANCELLED,
            BookingStatus.REIMBURSED,
        ],
    )
    @clean_database
    @patch("wtforms.csrf.session.SessionCSRF.validate_csrf_token")
    def test_delete_venue_rejected(self, mocked_validate_csrf_token, client, booking_status):
        admin = AdminFactory(email="user@example.com")
        venue = offers_factories.VenueFactory()
        offers_factories.UserOffererFactory(offerer=venue.managingOfferer)
        BookingFactory(stock__offer__venue=venue, status=booking_status)

        api_client = client.with_session_auth(admin.email)
        response = api_client.post(
            "/pc/back-office/venue/delete/", form={"id": venue.id, "url": "/pc/back-office/venue/"}
        )

        assert response.status_code == 302

        list_response = api_client.get(response.headers["location"])
        assert "Impossible d&#39;effacer un lieu pour lequel il existe des réservations." in list_response.data.decode(
            "utf8"
        )

        assert len(Venue.query.all()) == 1
        assert len(sendinblue_testing.sendinblue_requests) == 0


class GetVenueProviderLinkTest:
    @pytest.mark.usefixtures("db_session")
    def test_return_empty_link_when_no_venue_provider(self, app):
        # Given
        venue = offers_factories.VenueFactory()

        # When
        link = _get_venue_provider_link(None, None, venue, None)

        # Then
        assert not link

    @pytest.mark.usefixtures("db_session")
    def test_return_link_to_venue_provider(self, app):
        # Given
        venue_provider = providers_factories.VenueProviderFactory()
        venue = venue_provider.venue

        # When
        link = _get_venue_provider_link(None, None, venue, None)

        # Then
        assert str(venue.id) in link


class VenueForOffererSubviewTest:
    @clean_database
    @patch("wtforms.csrf.session.SessionCSRF.validate_csrf_token")
    def test_list_venues_for_offerer(self, mocked_validate_csrf_token, client):
        admin = AdminFactory(email="user@example.com")
        offerer = offers_factories.OffererFactory()
        venue1 = offers_factories.VenueFactory(managingOfferer=offerer)
        venue2 = offers_factories.VenueFactory(managingOfferer=offerer)
        offers_factories.VenueFactory()  # not expected result

        api_client = client.with_session_auth(admin.email)
        response = api_client.get(f"/pc/back-office/venue_for_offerer/?id={offerer.id}")

        assert response.status_code == 200

        # Check venues in html content
        regex = r'<td class="col-id">\s+(\d+)\s+</td>'
        venue_ids = re.findall(regex, response.data.decode("utf8"))

        assert sorted(venue_ids) == sorted([str(venue1.id), str(venue2.id)])
