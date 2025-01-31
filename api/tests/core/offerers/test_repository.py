import pytest

from pcapi.core.offerers import exceptions
from pcapi.core.offerers import models
from pcapi.core.offerers import repository
import pcapi.core.offerers.factories as offerers_factories
import pcapi.core.offers.factories as offers_factories
import pcapi.core.offers.models as offers_models
from pcapi.core.users import factories as users_factories
from pcapi.models.bank_information import BankInformationStatus


pytestmark = pytest.mark.usefixtures("db_session")


class GetAllVenueLabelsTest:
    def test_get_all_venue_labels(self):
        label1 = offerers_factories.VenueLabelFactory()
        label2 = offerers_factories.VenueLabelFactory()

        assert set(repository.get_all_venue_labels()) == {label1, label2}


class GetAllOfferersForUserTest:
    def should_return_all_offerers_for_an_admin(self) -> None:
        # Given
        admin = users_factories.AdminFactory()
        offerer = offers_factories.OffererFactory()

        # When
        offerers = repository.get_all_offerers_for_user(user=admin).all()

        # Then
        assert len(offerers) == 1
        assert offerers[0].id == offerer.id

    def should_return_pro_offerers_only(self) -> None:
        # Given
        pro = users_factories.ProFactory()
        pro_offerer_attachment = offerers_factories.UserOffererFactory(user=pro)
        other_offerer = offers_factories.OffererFactory()

        # When
        offerers = repository.get_all_offerers_for_user(user=pro).all()

        # Then
        assert len(offerers) == 1
        offerers_ids = [offerer.id for offerer in offerers]
        assert pro_offerer_attachment.offerer.id in offerers_ids
        assert other_offerer.id not in offerers_ids

    def should_return_non_validated_offerers(self) -> None:
        # Given
        pro = users_factories.ProFactory()
        pro_offerer_attachment = offerers_factories.UserOffererFactory(user=pro, offerer__validationToken="Token")

        # When
        offerers = repository.get_all_offerers_for_user(user=pro).all()

        # Then
        assert len(offerers) == 1
        offerers_ids = [offerer.id for offerer in offerers]
        assert pro_offerer_attachment.offerer.id in offerers_ids

    def should_return_offerers_with_non_validated_attachment_to_given_pro(self) -> None:
        # Given
        pro = users_factories.ProFactory()
        unvalidated_pro_offerer_attachment = offerers_factories.UserOffererFactory(user=pro, validationToken="Token")

        # When
        offerers = repository.get_all_offerers_for_user(user=pro).all()

        # Then
        assert len(offerers) == 1
        offerers_ids = [offerer.id for offerer in offerers]
        assert unvalidated_pro_offerer_attachment.offerer.id in offerers_ids

    def should_not_return_deactivated_offerers(self) -> None:
        # Given
        admin = users_factories.AdminFactory()
        offers_factories.OffererFactory(isActive=False)

        # When
        offerers = repository.get_all_offerers_for_user(user=admin).all()

        # Then
        assert len(offerers) == 0

    def test_search_keywords_in_offerer_name(self):
        offerer1 = offers_factories.OffererFactory(name="cinéma")
        offerer2 = offers_factories.OffererFactory(name="théâtre")
        pro = users_factories.ProFactory(offerers=[offerer1, offerer2])

        offerers = repository.get_all_offerers_for_user(user=pro, keywords="cinema").all()

        assert len(offerers) == 1
        assert offerers == [offerer1]

    def test_search_keywords_in_venue_name(self):
        offerer1 = offers_factories.OffererFactory(name="dummy")
        offers_factories.VenueFactory(managingOfferer=offerer1, name="cinéma")
        offerer2 = offers_factories.OffererFactory(name="dummy")
        offers_factories.VenueFactory(managingOfferer=offerer2, name="théâtre")
        pro = users_factories.ProFactory(offerers=[offerer1, offerer2])

        offerers = repository.get_all_offerers_for_user(user=pro, keywords="cinema").all()

        assert len(offerers) == 1
        assert offerers == [offerer1]

    class WithValidatedFilterTest:
        def should_return_all_pro_offerers_when_filter_is_none(self) -> None:
            # Given
            pro = users_factories.ProFactory()
            pro_attachment_to_validated_offerer = offerers_factories.UserOffererFactory(user=pro)
            pro_attachment_to_unvalidated_offerer = offerers_factories.UserOffererFactory(
                user=pro, offerer__validationToken="Token"
            )

            # When
            offerers = repository.get_all_offerers_for_user(user=pro).all()

            # Then
            assert len(offerers) == 2
            offerers_ids = [offerer.id for offerer in offerers]
            assert pro_attachment_to_validated_offerer.offerer.id in offerers_ids
            assert pro_attachment_to_unvalidated_offerer.offerer.id in offerers_ids

        def should_return_only_validated_offerers_when_filter_is_true(self) -> None:
            # Given
            pro = users_factories.ProFactory()
            pro_attachment_to_validated_offerer = offerers_factories.UserOffererFactory(user=pro)
            pro_attachment_to_unvalidated_offerer = offerers_factories.UserOffererFactory(
                user=pro, offerer__validationToken="Token"
            )

            # When
            offerers = repository.get_all_offerers_for_user(user=pro, validated=True).all()

            # Then
            assert len(offerers) == 1
            offerers_ids = [offerer.id for offerer in offerers]
            assert pro_attachment_to_validated_offerer.offerer.id in offerers_ids
            assert pro_attachment_to_unvalidated_offerer.offerer.id not in offerers_ids

        def should_return_only_unvalidated_offerers_when_filter_is_false(self) -> None:
            # Given
            pro = users_factories.ProFactory()
            pro_attachment_to_validated_offerer = offerers_factories.UserOffererFactory(user=pro)
            pro_attachment_to_unvalidated_offerer = offerers_factories.UserOffererFactory(
                user=pro, offerer__validationToken="Token"
            )

            # When
            offerers = repository.get_all_offerers_for_user(user=pro, validated=False).all()

            # Then
            assert len(offerers) == 1
            offerers_ids = [offerer.id for offerer in offerers]
            assert pro_attachment_to_validated_offerer.offerer.id not in offerers_ids
            assert pro_attachment_to_unvalidated_offerer.offerer.id in offerers_ids

    class WithValidatedForUserFilterTest:
        def should_return_all_pro_offerers_when_filter_is_none(self) -> None:
            # Given
            pro = users_factories.ProFactory()
            validated_pro_offerer_attachment = offerers_factories.UserOffererFactory(user=pro)
            unvalidated_pro_offerer_attachment = offerers_factories.UserOffererFactory(
                user=pro, validationToken="Token"
            )

            # When
            offerers = repository.get_all_offerers_for_user(user=pro).all()

            # Then
            assert len(offerers) == 2
            offerers_ids = [offerer.id for offerer in offerers]
            assert validated_pro_offerer_attachment.offerer.id in offerers_ids
            assert unvalidated_pro_offerer_attachment.offerer.id in offerers_ids

        def should_return_only_offerers_with_validated_attachment_when_filter_is_true(self) -> None:
            # Given
            pro = users_factories.ProFactory()
            validated_pro_offerer_attachment = offerers_factories.UserOffererFactory(user=pro)
            unvalidated_pro_offerer_attachment = offerers_factories.UserOffererFactory(
                user=pro, validationToken="Token"
            )

            # When
            offerers = repository.get_all_offerers_for_user(user=pro, validated_for_user=True).all()

            # Then
            assert len(offerers) == 1
            offerers_ids = [offerer.id for offerer in offerers]
            assert validated_pro_offerer_attachment.offerer.id in offerers_ids
            assert unvalidated_pro_offerer_attachment.offerer.id not in offerers_ids

        def should_return_only_offerers_with_unvalidated_attachment_when_filter_is_false(self) -> None:
            # Given
            pro = users_factories.ProFactory()
            validated_pro_offerer_attachment = offerers_factories.UserOffererFactory(user=pro)
            unvalidated_pro_offerer_attachment = offerers_factories.UserOffererFactory(
                user=pro, validationToken="Token"
            )

            # When
            offerers = repository.get_all_offerers_for_user(user=pro, validated_for_user=False).all()

            # Then
            assert len(offerers) == 1
            offerers_ids = [offerer.id for offerer in offerers]
            assert validated_pro_offerer_attachment.offerer.id not in offerers_ids
            assert unvalidated_pro_offerer_attachment.offerer.id in offerers_ids


class FindUserOffererByValidationTokenTest:
    def test_return_user_offerer_given_validation_token(self):
        # Given
        user_offerer_expected = offerers_factories.UserOffererFactory(validationToken="TOKEN")

        # When
        user_offerer_received = repository.find_user_offerer_by_validation_token(user_offerer_expected.validationToken)

        # Then
        assert user_offerer_received.id == user_offerer_expected.id

    def test_return_nothing_when_validation_token_does_not_exist(self):
        # Given
        offerers_factories.UserOffererFactory(validationToken="TOKEN")

        # When
        user_offerer_received = repository.find_user_offerer_by_validation_token("ANOTHER TOKEN")

        # Then
        assert user_offerer_received is None


class FindOffererByValidationTokenTest:
    def test_return_offerer_given_validation_token(self):
        # Given
        user_offerer_expected = offerers_factories.UserOffererFactory(offerer__validationToken="TOKEN")

        # When
        offerer_received = repository.find_offerer_by_validation_token(user_offerer_expected.offerer.validationToken)

        # Then
        assert offerer_received.id == user_offerer_expected.offerer.id

    def test_return_nothing_when_validation_token_does_not_exist(self):
        # Given
        offerers_factories.UserOffererFactory(offerer__validationToken="TOKEN")

        # When
        offerer_received = repository.find_offerer_by_validation_token("ANOTHER TOKEN")

        # Then
        assert offerer_received is None


class FindNewOffererUserEmailTest:
    def test_find_existing_email(self):
        offerer = offerers_factories.OffererFactory()
        pro_user = users_factories.ProFactory()
        offerers_factories.UserOffererFactory(offerer=offerer, user=pro_user)

        result = repository.find_new_offerer_user_email(offerer.id)

        assert result == pro_user.email

    def test_find_unknown_email(self):
        with pytest.raises(exceptions.CannotFindOffererUserEmail):
            repository.find_new_offerer_user_email(offerer_id=1)


class FilterOfferersWithKeywordsStringTest:
    def test_find_filtered_offerers_with_keywords(self):
        offerer_with_only_virtual_venue_with_offer = offerers_factories.OffererFactory(siren="123456785")
        offerer_with_both_venues_offer_on_both = offerers_factories.OffererFactory(siren="123456782")
        offerer_with_both_venues_offer_on_virtual = offerers_factories.OffererFactory(siren="123456783")
        offerer_with_both_venues_offer_on_not_virtual = offerers_factories.OffererFactory(siren="123456784")

        virtual_venue_with_offer_1 = offers_factories.VenueFactory(
            managingOfferer=offerer_with_only_virtual_venue_with_offer, isVirtual=True, siret=None
        )
        virtual_venue_with_offer_3 = offers_factories.VenueFactory(
            managingOfferer=offerer_with_both_venues_offer_on_both,
            isVirtual=True,
            siret=None,
            publicName="Librairie des mots perdus",
        )
        venue_with_offer_3 = offers_factories.VenueFactory(
            managingOfferer=offerer_with_both_venues_offer_on_both,
            siret="12345678212345",
            publicName="Librairie des mots perdus",
        )
        virtual_venue_with_offer_4 = offers_factories.VenueFactory(
            managingOfferer=offerer_with_both_venues_offer_on_virtual,
            isVirtual=True,
            siret=None,
            publicName="Librairie des mots perdus",
        )
        venue_with_offer_5 = offers_factories.VenueFactory(
            managingOfferer=offerer_with_both_venues_offer_on_not_virtual,
            siret="12345678412345",
            publicName="Librairie des mots perdus",
        )
        offers_factories.VenueFactory(publicName="something else")

        offers_factories.ThingOfferFactory(venue=virtual_venue_with_offer_1, url="http://url.com")
        offers_factories.ThingOfferFactory(venue=virtual_venue_with_offer_3, url="http://url.com")
        offers_factories.ThingOfferFactory(venue=virtual_venue_with_offer_4, url="http://url.com")
        offers_factories.EventOfferFactory(venue=venue_with_offer_3)
        offers_factories.EventOfferFactory(venue=venue_with_offer_5)

        one_keyword_search = repository.filter_offerers_with_keywords_string(
            models.Offerer.query.join(models.Venue), "perdus"
        )
        partial_keyword_search = repository.filter_offerers_with_keywords_string(
            models.Offerer.query.join(models.Venue), "Libr"
        )
        two_keywords_search = repository.filter_offerers_with_keywords_string(
            models.Offerer.query.join(models.Venue), "Librairie perd"
        )
        two_partial_keywords_search = repository.filter_offerers_with_keywords_string(
            models.Offerer.query.join(models.Venue), "Lib perd"
        )

        assert {
            offerer_with_both_venues_offer_on_both,
            offerer_with_both_venues_offer_on_virtual,
            offerer_with_both_venues_offer_on_not_virtual,
        } == set(one_keyword_search)
        assert {
            offerer_with_both_venues_offer_on_both,
            offerer_with_both_venues_offer_on_virtual,
            offerer_with_both_venues_offer_on_not_virtual,
        } == set(partial_keyword_search)
        assert {
            offerer_with_both_venues_offer_on_both,
            offerer_with_both_venues_offer_on_virtual,
            offerer_with_both_venues_offer_on_not_virtual,
        } == set(two_keywords_search)
        assert {
            offerer_with_both_venues_offer_on_both,
            offerer_with_both_venues_offer_on_virtual,
            offerer_with_both_venues_offer_on_not_virtual,
        } == set(two_partial_keywords_search)


@pytest.mark.usefixtures("db_session")
def test_filter_query_where_user_is_user_offerer_and_is_validated():
    # Given
    offer1 = offers_factories.OfferFactory()
    offer2 = offers_factories.OfferFactory()
    offer3 = offers_factories.OfferFactory()
    offerer1 = offer1.venue.managingOfferer
    offerer2 = offer2.venue.managingOfferer
    pro = users_factories.ProFactory()
    offerers_factories.UserOffererFactory(user=pro, offerer=offerer1)
    offerers_factories.UserOffererFactory(user=pro, offerer=offerer2)

    # When
    base_query = offers_models.Offer.query.join(models.Venue).join(models.Offerer)
    offers = repository.filter_query_where_user_is_user_offerer_and_is_validated(base_query, pro).all()

    # Then
    assert offer1 in offers
    assert offer2 in offers
    assert offer3 not in offers


class HasVenueWithoutDraftOrAcceptedBankInformationTest:
    def test_venue_with_accepted_bank_information(self):
        offerer = offerers_factories.OffererFactory()
        offers_factories.VirtualVenueFactory(managingOfferer=offerer)
        venue = offers_factories.VenueFactory(managingOfferer=offerer)
        offers_factories.BankInformationFactory(venue=venue, status=BankInformationStatus.ACCEPTED)

        assert not repository.has_physical_venue_without_draft_or_accepted_bank_information(offerer_id=offerer.id)

    def test_venue_with_draft_bank_information(self):
        offerer = offerers_factories.OffererFactory()
        offers_factories.VirtualVenueFactory(managingOfferer=offerer)
        venue = offers_factories.VenueFactory(managingOfferer=offerer)
        offers_factories.BankInformationFactory(venue=venue, status=BankInformationStatus.DRAFT)

        assert not repository.has_physical_venue_without_draft_or_accepted_bank_information(offerer_id=offerer.id)

    def test_venues_with_rejected_and_accepted_bank_information(self):
        offerer = offerers_factories.OffererFactory()
        offers_factories.VirtualVenueFactory(managingOfferer=offerer)
        venue_with_rejected_bank_information = offers_factories.VenueFactory(managingOfferer=offerer)
        offers_factories.BankInformationFactory(
            venue=venue_with_rejected_bank_information, status=BankInformationStatus.REJECTED
        )
        venue_with_rejected_bank_information = offers_factories.VenueFactory(managingOfferer=offerer)
        offers_factories.BankInformationFactory(
            venue=venue_with_rejected_bank_information, status=BankInformationStatus.ACCEPTED
        )

        assert repository.has_physical_venue_without_draft_or_accepted_bank_information(offerer_id=offerer.id)

    def test_venues_with_missing_and_accepted_bank_information(self):
        offerer = offerers_factories.OffererFactory()
        offers_factories.VirtualVenueFactory(managingOfferer=offerer)
        offers_factories.VenueFactory(managingOfferer=offerer)
        venue_with_rejected_bank_information = offers_factories.VenueFactory(managingOfferer=offerer)
        offers_factories.BankInformationFactory(
            venue=venue_with_rejected_bank_information, status=BankInformationStatus.ACCEPTED
        )

        assert repository.has_physical_venue_without_draft_or_accepted_bank_information(offerer_id=offerer.id)


class HasDigitalVenueWithAtLeastOneOfferTest:
    def test_digital_venue_with_offer(self):
        offerer = offerers_factories.OffererFactory()
        digital_venue = offers_factories.VirtualVenueFactory(managingOfferer=offerer)
        offers_factories.DigitalOfferFactory(venue=digital_venue)

        assert repository.has_digital_venue_with_at_least_one_offer(offerer.id)

    def test_digital_venue_without_offer(self):
        offerer = offerers_factories.OffererFactory()
        offers_factories.VirtualVenueFactory(managingOfferer=offerer)

        assert not repository.has_digital_venue_with_at_least_one_offer(offerer.id)


class GetSirenByOffererIdTest:
    def test_return_siren_for_offerer_id(self):
        offerer = offerers_factories.OffererFactory()

        assert repository.find_siren_by_offerer_id(offerer.id) == offerer.siren

    def test_return_error_when_no_siren_found(self):
        with pytest.raises(exceptions.CannotFindOffererSiren):
            repository.find_siren_by_offerer_id(0)
