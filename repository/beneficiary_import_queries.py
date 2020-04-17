from typing import List, Optional

from sqlalchemy import asc

from models import BeneficiaryImport, ImportStatus, User
from models.db import db
from repository import repository


def is_already_imported(application_id: int) -> bool:
    beneficiary_import = BeneficiaryImport.query \
        .filter(BeneficiaryImport.demarcheSimplifieeApplicationId == application_id) \
        .first()

    if beneficiary_import is None:
        return False

    return beneficiary_import.currentStatus != ImportStatus.RETRY


def save_beneficiary_import_with_status(status: ImportStatus,
                                        demarche_simplifiee_application_id: int,
                                        demarche_simplifiee_procedure_id: int,
                                        user: User = None,
                                        detail: str = None):
    existing_beneficiary_import = BeneficiaryImport.query \
        .filter_by(demarcheSimplifieeApplicationId=demarche_simplifiee_application_id) \
        .first()

    beneficiary_import = existing_beneficiary_import or BeneficiaryImport()
    if not beneficiary_import.beneficiary:
        beneficiary_import.beneficiary = user

    beneficiary_import.demarcheSimplifieeApplicationId = demarche_simplifiee_application_id
    beneficiary_import.demarcheSimplifieeProcedureId = demarche_simplifiee_procedure_id
    beneficiary_import.setStatus(status=status, detail=detail, author=None)

    repository.save(beneficiary_import)


def find_applications_ids_to_retry() -> List[int]:
    ids = db.session \
        .query(BeneficiaryImport.demarcheSimplifieeApplicationId) \
        .filter(BeneficiaryImport.currentStatus == ImportStatus.RETRY) \
        .order_by(asc(BeneficiaryImport.demarcheSimplifieeApplicationId)) \
        .all()

    return sorted(list(map(lambda result_set: result_set[0], ids)))
