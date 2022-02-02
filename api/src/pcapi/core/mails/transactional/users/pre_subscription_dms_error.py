from typing import Optional

from pcapi.core import mails
from pcapi.core.mails.transactional.sendinblue_template_ids import SendinblueTransactionalEmailData
from pcapi.core.mails.transactional.sendinblue_template_ids import TransactionalEmail


def get_pre_subscription_dms_error_email_data(
    postal_code_value: Optional[str], id_piece_number_value: Optional[str]
) -> SendinblueTransactionalEmailData:
    data = SendinblueTransactionalEmailData(template=TransactionalEmail.PRE_SUBSCRIPTION_DMS_ERROR_TO_BENEFICIARY.value)
    assert postal_code_value != None or id_piece_number_value != None
    if postal_code_value:
        data.params["FIELD_NAME1"] = "Code Postal"
        data.params["FIELD_INPUT1"] = postal_code_value
    if id_piece_number_value:
        data.params["FIELD_NAME2"] = "N° de pièce d'identité"
        data.params["FIELD_INPUT2"] = id_piece_number_value
    return data


def send_pre_subscription_from_dms_error_email_to_beneficiary(
    user_email: str, postal_code: Optional[str], id_piece_number: Optional[str]
) -> bool:
    data = get_pre_subscription_dms_error_email_data(postal_code, id_piece_number)
    return mails.send(recipients=[user_email], data=data)
