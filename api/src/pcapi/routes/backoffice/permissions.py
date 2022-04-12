import logging

from pcapi.core.permissions import api as perm_api
from pcapi.serialization.decorator import spectree_serialize

from . import blueprint
from .serialization import Role


logger = logging.getLogger(__name__)


@blueprint.backoffice_blueprint.route("/roles")
@spectree_serialize(
    response_model=Role,
    on_success_status=200,
    api=blueprint.api,
)
# FIXME (ASK, 2022/04/12): ajouter ici la vérification des permissions
def list_roles():
    roles = perm_api.list_roles()
    return Role.from_orm(roles)
