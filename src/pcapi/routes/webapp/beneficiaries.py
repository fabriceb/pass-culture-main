from typing import Tuple

from flask import jsonify
from flask import request
from flask_login import current_user
from flask_login import login_required
from flask_login import login_user

from pcapi import settings
from pcapi.core.users import exceptions as users_exceptions
from pcapi.core.users import repository as users_repo
from pcapi.flask_app import private_api
from pcapi.flask_app import public_api
from pcapi.models.api_errors import ApiErrors
from pcapi.routes.serialization import as_dict
from pcapi.routes.serialization import beneficiaries as serialization_beneficiaries
from pcapi.serialization.decorator import spectree_serialize
from pcapi.use_cases.update_user_informations import AlterableUserInformations
from pcapi.use_cases.update_user_informations import update_user_informations
from pcapi.utils.includes import BENEFICIARY_INCLUDES
from pcapi.utils.login_manager import stamp_session
from pcapi.utils.rest import expect_json_data
from pcapi.utils.rest import login_or_api_key_required
from pcapi.validation.routes.captcha import check_recaptcha_token_is_valid
from pcapi.validation.routes.users import check_allowed_changes_for_user
from pcapi.validation.routes.users import check_valid_signin
from pcapi.workers.beneficiary_job import beneficiary_job


# @debt api-migration
@private_api.route("/beneficiaries/current", methods=["GET"])
@login_required
def get_beneficiary_profile() -> Tuple[str, int]:
    user = current_user._get_current_object()
    return jsonify(as_dict(user, includes=BENEFICIARY_INCLUDES)), 200


# @debt api-migration
@private_api.route("/beneficiaries/current", methods=["PATCH"])
@login_or_api_key_required
@expect_json_data
def patch_beneficiary() -> Tuple[str, int]:
    data = request.json.keys()
    check_allowed_changes_for_user(data)

    user_informations = AlterableUserInformations(
        id=current_user.id,
        cultural_survey_id=request.json.get("culturalSurveyId"),
        cultural_survey_filled_date=request.json.get("culturalSurveyFilledDate"),
        department_code=request.json.get("departementCode"),
        email=request.json.get("email"),
        last_connection_date=request.json.get("lastConnectionDate"),
        needs_to_fill_cultural_survey=request.json.get("needsToFillCulturalSurvey"),
        phone_number=request.json.get("phoneNumber"),
        postal_code=request.json.get("postalCode"),
        public_name=request.json.get("publicName"),
        has_seen_tutorials=request.json.get("hasSeenTutorials"),
    )
    user = update_user_informations(user_informations)

    formattedUser = as_dict(user, includes=BENEFICIARY_INCLUDES)
    return jsonify(formattedUser), 200


# @debt api-migration
@private_api.route("/beneficiaries/signin", methods=["POST"])
def signin_beneficiary() -> Tuple[str, int]:
    json = request.get_json()
    identifier = json.get("identifier")
    password = json.get("password")
    check_valid_signin(identifier, password)
    errors = ApiErrors()
    errors.status_code = 401
    try:
        user = users_repo.get_user_with_credentials(identifier, password)
    except users_exceptions.InvalidIdentifier as exc:
        errors.add_error("identifier", "Identifiant incorrect")
        raise errors from exc
    except users_exceptions.UnvalidatedAccount as exc:
        errors.add_error("identifier", "Ce compte n'est pas validé.")
        raise errors from exc
    except users_exceptions.InvalidPassword as exc:
        errors.add_error("password", "Mot de passe incorrect")
        raise errors from exc
    login_user(user, remember=True)
    stamp_session(user)
    return jsonify(), 200


@public_api.route("/beneficiaries/licence_verify", methods=["POST"])
@spectree_serialize(
    response_model=serialization_beneficiaries.VerifyIdCheckLicenceResponse,
    on_success_status=200,
    on_error_statuses=[400, 422],
)
def verify_id_check_licence_token(
    body: serialization_beneficiaries.VerifyIdCheckLicenceRequest,
) -> serialization_beneficiaries.VerifyIdCheckLicenceResponse:
    if users_repo.get_id_check_token(body.token):
        return serialization_beneficiaries.VerifyIdCheckLicenceResponse()

    # Let's try with the legacy webapp tokens
    check_recaptcha_token_is_valid(body.token, "submit", settings.RECAPTCHA_LICENCE_MINIMAL_SCORE)

    return serialization_beneficiaries.VerifyIdCheckLicenceResponse()


@public_api.route("/beneficiaries/application_update", methods=["POST"])
@spectree_serialize(
    response_model=serialization_beneficiaries.ApplicationUpdateResponse, on_success_status=200, on_error_statuses=[400]
)
def id_check_application_update(
    body: serialization_beneficiaries.ApplicationUpdateRequest,
) -> serialization_beneficiaries.ApplicationUpdateResponse:
    try:
        application_id = int(body.id)
    except ValueError:
        raise ApiErrors({"id": "Not a number"})  # pylint: disable=raise-missing-from
    beneficiary_job.delay(application_id)
    return serialization_beneficiaries.ApplicationUpdateResponse()
