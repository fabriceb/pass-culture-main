from urllib.parse import quote

from pcapi.core.bookings import conf
from pcapi.core.users import models as users_models
from pcapi.models.deposit import DepositType
from pcapi.utils.urls import generate_firebase_dynamic_link


def get_activation_email_data(user: users_models.User, token: users_models.Token) -> dict:
    first_name = user.firstName.capitalize() if user.firstName else None
    email = user.email

    return {
        "Mj-TemplateID": 994771,
        "Mj-TemplateLanguage": True,
        "Vars": {
            "prenom_user": first_name,
            "token": token.value,
            "email": quote(email),
        },
    }


def get_accepted_as_beneficiary_email_data() -> dict:
    limit_configuration = conf.get_current_limit_configuration_for_type(DepositType.GRANT_18)
    deposit_amount = limit_configuration.TOTAL_CAP
    return {
        "Mj-TemplateID": 2016025,
        "Mj-TemplateLanguage": True,
        "Mj-campaign": "confirmation-credit",
        "Vars": {
            "depositAmount": int(deposit_amount),
        },
    }


def get_newly_eligible_user_email_data(user: users_models.User) -> dict:
    email_link = generate_firebase_dynamic_link(
        path="id-check",
        params={"email": user.email},
    )
    limit_configuration = conf.get_current_limit_configuration_for_type(DepositType.GRANT_18)
    deposit_amount = limit_configuration.TOTAL_CAP
    return {
        "Mj-TemplateID": 2030056,
        "Mj-TemplateLanguage": True,
        "Mj-trackclick": 1,
        "Vars": {
            "nativeAppLink": email_link,
            "depositAmount": int(deposit_amount),
        },
    }


def get_dms_application_data() -> dict:
    return {
        "Mj-TemplateID": 3062771,
        "Mj-TemplateLanguage": True,
    }
