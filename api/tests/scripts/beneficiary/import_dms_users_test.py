from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest.mock import patch

from dateutil.relativedelta import relativedelta
import freezegun
import pytest

from pcapi.connectors.api_demarches_simplifiees import DMSGraphQLClient
from pcapi.connectors.api_demarches_simplifiees import GraphQLApplicationStates
import pcapi.core.fraud.models as fraud_models
import pcapi.core.mails.testing as mails_testing
from pcapi.core.payments.models import Deposit
from pcapi.core.payments.models import DepositType
import pcapi.core.subscription.api as subscription_api
import pcapi.core.subscription.models as subscription_models
from pcapi.core.testing import override_features
from pcapi.core.users import api as users_api
from pcapi.core.users import factories as users_factories
from pcapi.core.users import models as users_models
from pcapi.core.users.constants import ELIGIBILITY_AGE_18
from pcapi.models.beneficiary_import import BeneficiaryImport
from pcapi.models.beneficiary_import import BeneficiaryImportSources
from pcapi.models.beneficiary_import_status import ImportStatus
import pcapi.notifications.push.testing as push_testing
from pcapi.scripts.beneficiary import import_dms_users

from tests.scripts.beneficiary.fixture import make_graphql_application
from tests.scripts.beneficiary.fixture import make_new_application
from tests.scripts.beneficiary.fixture import make_new_stranger_application


NOW = datetime.utcnow()

AGE18_ELIGIBLE_BIRTH_DATE = dateOfBirth = datetime.utcnow() - relativedelta(years=ELIGIBILITY_AGE_18)


@pytest.mark.usefixtures("db_session")
class RunTest:
    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    @patch("pcapi.core.subscription.api.on_successful_application")
    def test_should_retrieve_applications_from_new_procedure_id(
        self,
        on_sucessful_application,
        get_applications_with_details,
    ):
        get_applications_with_details.return_value = [
            make_graphql_application(123, "closed", email="email1@example.com", id_piece_number="123123121"),
            make_graphql_application(456, "closed", email="email2@example.com", id_piece_number="123123122"),
            make_graphql_application(789, "closed", email="email3@example.com", id_piece_number="123123123"),
        ]

        import_dms_users.run(procedure_id=6712558)
        assert get_applications_with_details.call_count == 1
        get_applications_with_details.assert_called_with(6712558, GraphQLApplicationStates.accepted)

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    @patch("pcapi.core.subscription.api.on_successful_application")
    def test_all_applications_are_processed_once(
        self,
        on_sucessful_application,
        get_applications_with_details,
    ):
        users_factories.UserFactory(email="email1@example.com")
        users_factories.UserFactory(email="email2@example.com")
        users_factories.UserFactory(email="email3@example.com")
        get_applications_with_details.return_value = [
            make_graphql_application(
                123,
                "closed",
                email="email1@example.com",
                id_piece_number="123123121",
                birth_date=AGE18_ELIGIBLE_BIRTH_DATE,
            ),
            make_graphql_application(
                456,
                "closed",
                email="email2@example.com",
                id_piece_number="123123122",
                birth_date=AGE18_ELIGIBLE_BIRTH_DATE,
            ),
            make_graphql_application(
                789,
                "closed",
                email="email3@example.com",
                id_piece_number="123123123",
                birth_date=AGE18_ELIGIBLE_BIRTH_DATE,
            ),
        ]

        import_dms_users.run(procedure_id=6712558)
        assert on_sucessful_application.call_count == 3

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    @patch("pcapi.scripts.beneficiary.import_dms_users.parse_beneficiary_information_graphql")
    def test_an_error_status_is_saved_when_an_application_is_not_parsable(
        self,
        mocked_parse_beneficiary_information,
        get_applications_with_details,
    ):
        get_applications_with_details.return_value = [make_graphql_application(123, "closed")]
        mocked_parse_beneficiary_information.side_effect = [Exception()]

        # when
        import_dms_users.run(procedure_id=6712558)

        # then
        beneficiary_import = BeneficiaryImport.query.first()
        assert beneficiary_import.currentStatus == ImportStatus.ERROR
        assert beneficiary_import.applicationId == 123
        assert beneficiary_import.detail == "Le dossier 123 contient des erreurs et a été ignoré - Procedure 6712558"

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    @patch("pcapi.core.subscription.api.on_successful_application")
    def test_application_with_known_application_id_are_not_processed(
        self,
        on_sucessful_application,
        get_applications_with_details,
    ):
        # given
        created_import = users_factories.BeneficiaryImportFactory(applicationId=123, source="demarches_simplifiees")
        users_factories.BeneficiaryImportStatusFactory(
            status=ImportStatus.CREATED,
            beneficiaryImport=created_import,
            author=None,
        )
        get_applications_with_details.return_value = [make_graphql_application(123, "closed")]

        # when
        import_dms_users.run(procedure_id=6712558)

        # then
        on_sucessful_application.assert_not_called()

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    @patch("pcapi.core.subscription.api.on_successful_application")
    def test_application_with_known_email_and_already_beneficiary_are_saved_as_rejected(
        self, on_sucessful_application, get_applications_with_details
    ):
        # same user, but different
        user = users_factories.BeneficiaryGrant18Factory(email="john.doe@example.com")
        get_applications_with_details.return_value = [
            make_graphql_application(123, "closed", email="john.doe@example.com")
        ]
        initial_beneficiary_import_id = user.beneficiaryImports[0].id

        import_dms_users.run(procedure_id=6712558)

        beneficiary_import = BeneficiaryImport.query.filter(
            BeneficiaryImport.id != initial_beneficiary_import_id
        ).first()
        details = [status.detail for status in beneficiary_import.statuses]
        assert beneficiary_import.currentStatus == ImportStatus.REJECTED
        assert beneficiary_import.applicationId == 123
        assert details == ["Compte existant avec cet email", "Voir les details dans la page support"]
        assert beneficiary_import.beneficiary == user
        on_sucessful_application.assert_not_called()

    @override_features(FORCE_PHONE_VALIDATION=False)
    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    @patch("pcapi.core.subscription.api.on_successful_application")
    def test_beneficiary_is_created_with_procedure_id(self, on_sucessful_application, get_applications_with_details):
        # given
        applicant = users_factories.UserFactory(firstName="Doe", lastName="John", email="john.doe@test.com")
        get_applications_with_details.return_value = [
            make_graphql_application(
                123, "closed", id_piece_number="123123121", email=applicant.email, birth_date=AGE18_ELIGIBLE_BIRTH_DATE
            )
        ]

        import_dms_users.run(procedure_id=6712558)

        on_sucessful_application.assert_called_with(
            user=applicant,
            source_data=fraud_models.DMSContent(
                last_name="Doe",
                first_name="John",
                civility="Mme",
                email="john.doe@test.com",
                application_id=123,
                procedure_id=6712558,
                department="67",
                phone="0123456789",
                birth_date=AGE18_ELIGIBLE_BIRTH_DATE.date(),
                activity="Étudiant",
                address="3 La Bigotais 22800 Saint-Donan",
                postal_code="67200",
                registration_datetime=datetime(2020, 5, 13, 9, 9, 46, tzinfo=timezone(timedelta(seconds=7200))),
                id_piece_number="123123121",
            ),
            eligibility_type=users_models.EligibilityType.AGE18,
            application_id=123,
            source_id=6712558,
            source=BeneficiaryImportSources.demarches_simplifiees,
        )


class ParseBeneficiaryInformationTest:
    @pytest.mark.parametrize(
        "department_code,expected_code",
        [("67 - Bas-Rhin", "67"), ("973 - Guyane", "973"), ("2B - Haute-Corse", "2B"), ("2a - Corse-du-Sud", "2a")],
    )
    def test_handles_department_code(self, department_code, expected_code):
        application_detail = make_graphql_application(1, "closed", department_code=department_code)
        information = import_dms_users.parse_beneficiary_information_graphql(application_detail, procedure_id=201201)
        assert information.department == expected_code

    @pytest.mark.parametrize(
        "postal_code,expected_code",
        [
            ("  93130  ", "93130"),
            ("67 200", "67200"),
            ("67 200 Strasbourg ", "67200"),
        ],
    )
    def test_handles_postal_codes(self, postal_code, expected_code):
        application_detail = make_graphql_application(1, "closed", postal_code=postal_code)
        information = import_dms_users.parse_beneficiary_information_graphql(application_detail, procedure_id=201201)
        assert information.postal_code == expected_code

    def test_handles_civility_parsing(self):
        # given
        application_detail = make_graphql_application(1, "closed", civility="M.")

        # when
        information = import_dms_users.parse_beneficiary_information_graphql(application_detail, procedure_id=201201)

        # then
        assert information.civility == "M."

    @pytest.mark.parametrize("activity", ["Étudiant", None])
    def test_handles_activity(self, activity):
        application_detail = make_graphql_application(1, "closed", activity=activity)
        information = import_dms_users.parse_beneficiary_information_graphql(application_detail, procedure_id=201201)
        assert information.activity == activity

    @pytest.mark.parametrize("possible_value", ["0123456789", " 0123456789", "0123456789 ", " 0123456789 "])
    def test_beneficiary_information_id_piece_number_with_spaces_graphql(self, possible_value):
        application_detail = make_graphql_application(1, "closed", id_piece_number=possible_value)
        information = import_dms_users.parse_beneficiary_information_graphql(application_detail, procedure_id=123123)

        assert information.id_piece_number == "0123456789"

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_new_procedure(self, get_applications_with_details):
        raw_data = make_new_application()
        content = import_dms_users.parse_beneficiary_information_graphql(raw_data, 32)
        assert content.last_name == "VALGEAN"
        assert content.first_name == "Jean"
        assert content.civility == "M"
        assert content.email == "jean.valgean@example.com"
        assert content.application_id == 5718303
        assert content.procedure_id == 32
        assert content.department == None
        assert content.birth_date == date(2004, 12, 19)
        assert content.phone == "0601010101"
        assert content.postal_code == "92700"
        assert content.activity == "Employé"
        assert content.address == "32 rue des sapins gris 21350 l'îsle à dent"
        assert content.id_piece_number == "F9GFAL123"

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_new_procedure_for_stranger_residents(self, get_applications_with_details):
        raw_data = make_new_stranger_application()
        content = import_dms_users.parse_beneficiary_information_graphql(raw_data, 32)
        assert content.last_name == "VALGEAN"
        assert content.first_name == "Jean"
        assert content.civility == "M"
        assert content.email == "jean.valgean@example.com"
        assert content.application_id == 5742994
        assert content.procedure_id == 32
        assert content.department == None
        assert content.birth_date == date(2006, 5, 12)
        assert content.phone == "0601010101"
        assert content.postal_code == "92700"
        assert content.activity == "Employé"
        assert content.address == "32 rue des sapins gris 21350 l'îsle à dent"
        assert content.id_piece_number == "K682T8YLO"


class ParsingErrorsTest:
    def test_beneficiary_information_postalcode_error(self):
        application_detail = make_graphql_application(1, "closed", postal_code="Strasbourg")
        with pytest.raises(ValueError) as exc_info:
            import_dms_users.parse_beneficiary_information_graphql(application_detail, procedure_id=123123)

        assert exc_info.value.errors["postal_code"] == "Strasbourg"

    @pytest.mark.parametrize("possible_value", ["Passeport n: XXXXX", "sans numéro"])
    def test_beneficiary_information_id_piece_number_error(self, possible_value):
        application_detail = make_graphql_application(1, "closed", id_piece_number=possible_value)

        with pytest.raises(ValueError) as exc_info:
            import_dms_users.parse_beneficiary_information_graphql(application_detail, procedure_id=123123)

        assert exc_info.value.errors["id_piece_number"] == possible_value


@pytest.mark.usefixtures("db_session")
class RunIntegrationTest:
    EMAIL = "john.doe@example.com"
    BENEFICIARY_BIRTH_DATE = date.today() - timedelta(days=6752)  # ~18.5 years

    @override_features(FORCE_PHONE_VALIDATION=False)
    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_import_user(self, get_applications_with_details):
        user = users_factories.UserFactory(
            firstName="john",
            lastName="doe",
            email="john.doe@example.com",
            dateOfBirth=AGE18_ELIGIBLE_BIRTH_DATE,
        )

        get_applications_with_details.return_value = [
            make_graphql_application(application_id=123, state="closed", email=user.email)
        ]
        import_dms_users.run(procedure_id=6712558)

        assert users_models.User.query.count() == 1
        user = users_models.User.query.first()
        assert user.firstName == "John"
        assert user.postalCode == "67200"
        assert user.address == "3 La Bigotais 22800 Saint-Donan"
        assert user.phoneNumber == "0123456789"

        assert BeneficiaryImport.query.count() == 1

        beneficiary_import = BeneficiaryImport.query.first()
        assert beneficiary_import.source == "demarches_simplifiees"
        assert beneficiary_import.applicationId == 123
        assert beneficiary_import.beneficiary == user
        assert beneficiary_import.currentStatus == ImportStatus.CREATED
        assert len(push_testing.requests) == 2

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_import_exunderage_beneficiary(self, get_applications_with_details):
        with freezegun.freeze_time(datetime.utcnow() - relativedelta(years=2, month=1)):
            user = users_factories.UnderageBeneficiaryFactory(
                email="john.doe@example.com",
                firstName="john",
                lastName="doe",
                dateOfBirth=AGE18_ELIGIBLE_BIRTH_DATE,
                subscription_age=15,
            )
        details = make_graphql_application(application_id=123, state="closed", email=user.email)
        details["datePassageEnConstruction"] = datetime.now().isoformat()
        get_applications_with_details.return_value = [details]
        import_dms_users.run(procedure_id=6712558)

        assert users_models.User.query.count() == 1
        user = users_models.User.query.first()
        assert user.has_beneficiary_role
        deposits = Deposit.query.filter_by(user=user).all()
        age_18_deposit = next(deposit for deposit in deposits if deposit.type == DepositType.GRANT_18)
        assert len(deposits) == 2
        assert age_18_deposit.amount == 300
        assert BeneficiaryImport.query.count() == 2

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_import_user_requires_pre_creation(self, get_applications_with_details):
        # when
        get_applications_with_details.return_value = [
            make_graphql_application(application_id=123, state="closed", email="nonexistant@example.com")
        ]

        import_dms_users.run(procedure_id=6712558)
        beneficiary_import = BeneficiaryImport.query.first()
        assert beneficiary_import.source == "demarches_simplifiees"
        assert beneficiary_import.applicationId == 123
        assert beneficiary_import.currentStatus == ImportStatus.ERROR
        assert beneficiary_import.statuses[-1].detail == "Aucun utilisateur trouvé pour l'email nonexistant@example.com"

    @override_features(FORCE_PHONE_VALIDATION=True)
    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_phone_not_validated_create_beneficiary_with_phone_to_validate(self, get_applications_with_details):
        """
        Test that an imported user without a validated phone number, and the
        FORCE_PHONE_VALIDATION feature flag activated, requires a future validation
        """
        date_of_birth = self.BENEFICIARY_BIRTH_DATE.strftime("%Y-%m-%dT%H:%M:%S")

        # Create a user that has validated its email and phone number, meaning it
        # should become beneficiary.
        user = users_factories.UserFactory(
            email=self.EMAIL,
            isEmailValidated=True,
            dateOfBirth=date_of_birth,
            phoneValidationStatus=None,
        )
        get_applications_with_details.return_value = [
            make_graphql_application(application_id=123, state="closed", email=user.email)
        ]
        # when
        import_dms_users.run(procedure_id=6712558)

        # then
        assert users_models.User.query.count() == 1
        user = users_models.User.query.first()

        assert len(user.beneficiaryFraudChecks) == 2

        honor_check = fraud_models.BeneficiaryFraudCheck.query.filter_by(
            user=user, type=fraud_models.FraudCheckType.HONOR_STATEMENT
        ).one_or_none()
        assert honor_check
        dms_check = fraud_models.BeneficiaryFraudCheck.query.filter_by(
            user=user, type=fraud_models.FraudCheckType.DMS, status=fraud_models.FraudCheckStatus.OK
        ).one_or_none()
        assert dms_check
        assert BeneficiaryImport.query.count() == 1

        beneficiary_import = BeneficiaryImport.query.first()
        assert beneficiary_import.source == "demarches_simplifiees"
        assert beneficiary_import.applicationId == 123
        assert beneficiary_import.beneficiary == user
        assert beneficiary_import.currentStatus == ImportStatus.CREATED
        assert len(push_testing.requests) == 2

        assert not user.is_beneficiary
        assert not user.deposit
        assert (
            subscription_api.get_next_subscription_step(user) == subscription_models.SubscriptionStep.PHONE_VALIDATION
        )

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_import_makes_user_beneficiary(self, get_applications_with_details):
        """
        Test that an existing user with its phone number validated can become
        beneficiary.
        """
        date_of_birth = self.BENEFICIARY_BIRTH_DATE.strftime("%Y-%m-%dT%H:%M:%S")

        # Create a user that has validated its email and phone number, meaning it
        # should become beneficiary.
        user = users_factories.UserFactory(
            email=self.EMAIL,
            isEmailValidated=True,
            dateOfBirth=date_of_birth,
            phoneValidationStatus=users_models.PhoneValidationStatusType.VALIDATED,
        )
        get_applications_with_details.return_value = [
            make_graphql_application(application_id=123, state="closed", email=user.email)
        ]

        import_dms_users.run(procedure_id=6712558)

        assert users_models.User.query.count() == 1
        user = users_models.User.query.first()

        assert user.firstName == "John"
        assert user.postalCode == "67200"
        assert user.address == "3 La Bigotais 22800 Saint-Donan"
        assert user.has_beneficiary_role
        assert user.phoneNumber == "0123456789"
        assert user.idPieceNumber == "123123123"

        assert len(user.beneficiaryFraudChecks) == 2

        dms_fraud_check = next(
            fraud_check
            for fraud_check in user.beneficiaryFraudChecks
            if fraud_check.type == fraud_models.FraudCheckType.DMS
        )
        assert dms_fraud_check.type == fraud_models.FraudCheckType.DMS
        fraud_content = fraud_models.DMSContent(**dms_fraud_check.resultContent)
        assert fraud_content.birth_date == user.dateOfBirth.date()
        assert fraud_content.address == "3 La Bigotais 22800 Saint-Donan"

        assert next(
            fraud_check
            for fraud_check in user.beneficiaryFraudChecks
            if fraud_check.type == fraud_models.FraudCheckType.HONOR_STATEMENT
        )

        assert BeneficiaryImport.query.count() == 1
        beneficiary_import = BeneficiaryImport.query.first()

        assert beneficiary_import.source == "demarches_simplifiees"
        assert beneficiary_import.applicationId == 123
        assert beneficiary_import.beneficiary == user
        assert beneficiary_import.currentStatus == ImportStatus.CREATED
        assert len(push_testing.requests) == 2

        assert len(push_testing.requests) == 2

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_import_makes_user_beneficiary_after_19_birthday(self, get_applications_with_details):
        date_of_birth = (datetime.now() - relativedelta(years=19)).strftime("%Y-%m-%dT%H:%M:%S")

        # Create a user that has validated its email and phone number, meaning it
        # should become beneficiary.
        user = users_factories.UserFactory(
            email=self.EMAIL,
            isEmailValidated=True,
            dateOfBirth=date_of_birth,
            phoneValidationStatus=users_models.PhoneValidationStatusType.VALIDATED,
        )
        get_applications_with_details.return_value = [
            make_graphql_application(application_id=123, state="closed", email=user.email)
        ]
        import_dms_users.run(procedure_id=6712558)

        user = users_models.User.query.one()

        assert user.roles == [users_models.UserRole.BENEFICIARY]

    @override_features(FORCE_PHONE_VALIDATION=False)
    @freezegun.freeze_time("2021-10-30 09:00:00")
    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_import_duplicated_user(self, get_applications_with_details):
        existing_user = users_factories.BeneficiaryGrant18Factory(
            firstName="John",
            lastName="Doe",
            email="john.doe.beneficiary@example.com",
            dateOfBirth=self.BENEFICIARY_BIRTH_DATE,
            idPieceNumber="1234123432",
            isEmailValidated=True,
            isActive=True,
        )

        user = users_factories.UserFactory(
            firstName="john",
            lastName="doe",
            email="john.doe@example.com",
            dateOfBirth=existing_user.dateOfBirth,
            isEmailValidated=True,
            isActive=True,
        )

        get_applications_with_details.return_value = [
            make_graphql_application(
                application_id=123, state="closed", email=user.email, birth_date=self.BENEFICIARY_BIRTH_DATE
            )
        ]
        import_dms_users.run(procedure_id=6712558)

        assert users_models.User.query.count() == 2

        assert BeneficiaryImport.query.filter_by(beneficiary=user).count() == 1
        user = users_models.User.query.get(user.id)
        assert len(user.beneficiaryFraudChecks) == 1
        fraud_check = user.beneficiaryFraudChecks[0]
        assert fraud_check.type == fraud_models.FraudCheckType.DMS
        assert fraud_models.FraudReasonCode.DUPLICATE_USER in fraud_check.reasonCodes
        assert fraud_check.status == fraud_models.FraudCheckStatus.SUSPICIOUS

        beneficiary_import = BeneficiaryImport.query.filter(BeneficiaryImport.beneficiary != existing_user).first()
        assert beneficiary_import.source == "demarches_simplifiees"
        assert beneficiary_import.applicationId == 123
        assert beneficiary_import.currentStatus == ImportStatus.REJECTED
        sub_msg = user.subscriptionMessages[0]
        assert (
            sub_msg.userMessage
            == "Ton dossier a été bloqué : Il y a déjà un compte à ton nom sur le pass Culture. Tu peux contacter le support pour plus d'informations."
        )
        assert sub_msg.callToActionIcon == subscription_models.CallToActionIcon.EMAIL

    @override_features(FORCE_PHONE_VALIDATION=False)
    @freezegun.freeze_time("2021-10-30 09:00:00")
    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_import_with_existing_user_with_the_same_id_number(self, get_applications_with_details, mocker):
        beneficiary = users_factories.BeneficiaryGrant18Factory(idPieceNumber="1234123412")
        applicant = users_factories.UserFactory(
            email=self.EMAIL,
            isEmailValidated=True,
            dateOfBirth=self.BENEFICIARY_BIRTH_DATE,
            phoneValidationStatus=users_models.PhoneValidationStatusType.VALIDATED,
        )
        get_applications_with_details.return_value = [
            make_graphql_application(
                application_id=123,
                state="closed",
                email=applicant.email,
                id_piece_number="1234123412",
                birth_date=self.BENEFICIARY_BIRTH_DATE,
            )
        ]

        process_mock = mocker.patch("pcapi.core.subscription.api.on_successful_application")
        import_dms_users.run(procedure_id=6712558)

        assert process_mock.call_count == 0
        assert users_models.User.query.count() == 2

        fraud_check = applicant.beneficiaryFraudChecks[0]
        assert fraud_check.type == fraud_models.FraudCheckType.DMS

        assert fraud_check.status == fraud_models.FraudCheckStatus.SUSPICIOUS
        assert (
            fraud_check.reason == f"La pièce d'identité n°1234123412 est déjà prise par l'utilisateur {beneficiary.id}"
        )

        fraud_content = fraud_models.DMSContent(**fraud_check.resultContent)
        assert fraud_content.birth_date == applicant.dateOfBirth.date()
        assert fraud_content.address == "3 La Bigotais 22800 Saint-Donan"

        assert len(applicant.beneficiaryImports) == 1
        beneficiary_import = applicant.beneficiaryImports[0]
        assert len(beneficiary_import.statuses) == 1
        beneficiary_import_status = beneficiary_import.statuses[0]
        assert beneficiary_import.source == "demarches_simplifiees"
        assert beneficiary_import.applicationId == 123
        assert beneficiary_import.beneficiary == applicant
        assert beneficiary_import.currentStatus == ImportStatus.REJECTED
        assert beneficiary_import_status.beneficiaryImportId == beneficiary_import.id

        sub_msg = applicant.subscriptionMessages[0]
        assert (
            sub_msg.userMessage
            == "Ton dossier a été bloqué : Il y a déjà un compte à ton nom sur le pass Culture. Tu peux contacter le support pour plus d'informations."
        )
        assert sub_msg.callToActionIcon == subscription_models.CallToActionIcon.EMAIL

    @override_features(FORCE_PHONE_VALIDATION=False)
    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_import_native_app_user(self, get_applications_with_details):
        # given
        user = users_api.create_account(
            email=self.EMAIL,
            password="aBc123@567",
            birthdate=self.BENEFICIARY_BIRTH_DATE,
            is_email_validated=True,
            send_activation_mail=False,
            phone_number="0607080900",
        )
        push_testing.reset_requests()
        get_applications_with_details.return_value = [
            make_graphql_application(
                application_id=123,
                state="closed",
                email=user.email,
            )
        ]
        import_dms_users.run(procedure_id=6712558)

        # then
        assert users_models.User.query.count() == 1

        user = users_models.User.query.first()
        assert user.firstName == "John"
        assert user.postalCode == "67200"

        # Since the User already exists, the phone number should not be updated
        # during the import process
        assert user.phoneNumber == "0607080900"

        assert BeneficiaryImport.query.count() == 1

        beneficiary_import = BeneficiaryImport.query.first()
        assert beneficiary_import.source == "demarches_simplifiees"
        assert beneficiary_import.applicationId == 123
        assert beneficiary_import.beneficiary == user
        assert beneficiary_import.currentStatus == ImportStatus.CREATED

        assert len(mails_testing.outbox) == 1
        assert mails_testing.outbox[0].sent_data["Mj-TemplateID"] == 2016025

        assert len(push_testing.requests) == 2
        assert push_testing.requests[0]["attribute_values"]["u.is_beneficiary"]

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_dms_application_value_error(self, get_applications_with_details):
        get_applications_with_details.return_value = [
            make_graphql_application(
                application_id=123,
                state="closed",
                email="fake@example.com",
                postal_code="Strasbourg",
                id_piece_number="121314",
            )
        ]
        import_dms_users.run(procedure_id=6712558)

        beneficiary_import = BeneficiaryImport.query.first()
        assert beneficiary_import.currentStatus == ImportStatus.ERROR
        assert beneficiary_import.sourceId == 6712558
        assert (
            beneficiary_import.statuses[0].detail
            == "Erreur dans les données soumises dans le dossier DMS : 'id_piece_number' (121314),'postal_code' (Strasbourg)"
        )
        assert len(mails_testing.outbox) == 1
        assert mails_testing.outbox[0].sent_data["Mj-TemplateID"] == 3124925

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_dms_application_value_error_known_user(self, get_applications_with_details):
        user = users_factories.UserFactory()
        get_applications_with_details.return_value = [
            make_graphql_application(
                application_id=1, state="closed", postal_code="Strasbourg", id_piece_number="121314", email=user.email
            )
        ]
        import_dms_users.run(procedure_id=6712558)

        beneficiary_import = BeneficiaryImport.query.first()
        assert beneficiary_import.currentStatus == ImportStatus.ERROR
        assert beneficiary_import.sourceId == 6712558
        assert (
            beneficiary_import.statuses[0].detail
            == "Erreur dans les données soumises dans le dossier DMS : 'id_piece_number' (121314),'postal_code' (Strasbourg)"
        )
        assert beneficiary_import.beneficiary == user
        assert len(mails_testing.outbox) == 1
        assert mails_testing.outbox[0].sent_data["Mj-TemplateID"] == 3124925


@pytest.mark.usefixtures("db_session")
class GraphQLSourceProcessApplicationTest:
    def test_process_application_user_already_created(self):
        user = users_factories.UserFactory(dateOfBirth=AGE18_ELIGIBLE_BIRTH_DATE)
        application_id = 123123
        application_details = make_graphql_application(application_id, "closed", email=user.email)
        information = import_dms_users.parse_beneficiary_information_graphql(application_details, 123123)
        # fixture
        import_dms_users.process_application(
            123123,
            4234,
            information,
        )
        assert BeneficiaryImport.query.count() == 1
        import_status = BeneficiaryImport.query.one_or_none()
        assert import_status.currentStatus == ImportStatus.CREATED
        assert import_status.beneficiary == user
        assert len(user.beneficiaryFraudChecks) == 2
        dms_fraud_check = next(
            fraud_check
            for fraud_check in user.beneficiaryFraudChecks
            if fraud_check.type == fraud_models.FraudCheckType.DMS
        )
        assert not dms_fraud_check.reasonCodes
        assert dms_fraud_check.status == fraud_models.FraudCheckStatus.OK
        statement_fraud_check = next(
            fraud_check
            for fraud_check in user.beneficiaryFraudChecks
            if fraud_check.type == fraud_models.FraudCheckType.HONOR_STATEMENT
        )
        assert statement_fraud_check.status == fraud_models.FraudCheckStatus.OK
        assert statement_fraud_check.reason == "honor statement contained in DMS application"

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_run(self, get_applications_with_details):
        user = users_factories.UserFactory(
            dateOfBirth=AGE18_ELIGIBLE_BIRTH_DATE,
            subscriptionState=users_models.SubscriptionState.identity_check_pending,
        )
        application_id = 123123

        get_applications_with_details.return_value = [
            make_graphql_application(application_id, "closed", email=user.email)
        ]
        import_dms_users.run(123123)

        import_status = BeneficiaryImport.query.one_or_none()

        assert import_status.currentStatus == ImportStatus.CREATED
        assert import_status.beneficiary == user

        assert user.has_beneficiary_role
        assert user.is_subscriptionState_beneficiary_18()

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_dms_application_value_error(self, get_applications_with_details):
        user = users_factories.UserFactory()
        get_applications_with_details.return_value = [
            make_graphql_application(
                application_id=1, state="closed", postal_code="Strasbourg", id_piece_number="121314", email=user.email
            )
        ]

        import_dms_users.run(procedure_id=6712558)

        beneficiary_import = BeneficiaryImport.query.first()
        assert beneficiary_import.currentStatus == ImportStatus.ERROR
        assert beneficiary_import.sourceId == 6712558
        assert beneficiary_import.beneficiary == user
        assert (
            beneficiary_import.statuses[0].detail
            == "Erreur dans les données soumises dans le dossier DMS : 'id_piece_number' (121314),'postal_code' (Strasbourg)"
        )

        assert len(mails_testing.outbox) == 1
        assert mails_testing.outbox[0].sent_data["Mj-TemplateID"] == 3124925
        assert len(user.subscriptionMessages) == 1
        assert user.subscriptionMessages[0]
        assert (
            user.subscriptionMessages[0].userMessage
            == "Ton dossier déposé sur le site Démarches-Simplifiées a été refusé car les champs ‘ta pièce d'identité, ton code postal’ ne sont pas valides."
        )
        assert user.subscriptionMessages[0].popOverIcon == subscription_models.PopOverIcon.WARNING

    @patch.object(DMSGraphQLClient, "get_applications_with_details")
    def test_avoid_reimporting_already_imported_user(self, get_applications_with_details):
        procedure_id = 42
        user = users_factories.UserFactory(dateOfBirth=AGE18_ELIGIBLE_BIRTH_DATE)
        already_imported_user = users_factories.BeneficiaryGrant18Factory(beneficiaryImports=[])
        users_factories.BeneficiaryImportFactory(
            beneficiary=already_imported_user, applicationId=2, sourceId=procedure_id
        )
        get_applications_with_details.return_value = [
            make_graphql_application(application_id=1, state="closed", email=user.email),
            make_graphql_application(
                application_id=2,
                state="closed",
                email=already_imported_user.email,
            ),
        ]

        import_dms_users.run(procedure_id=procedure_id)

        imports = BeneficiaryImport.query.all()
        assert len(imports) == 2
        assert len(mails_testing.outbox) == 1
        sent_email = mails_testing.outbox[0]
        assert sent_email.sent_data["To"] == user.email
        assert sent_email.sent_data["Mj-campaign"] == "confirmation-credit"
