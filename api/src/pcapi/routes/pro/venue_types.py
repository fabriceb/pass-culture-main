from flask_login import login_required

from pcapi.core.offerers import models as offerers_models
from pcapi.routes.apis import private_api
from pcapi.routes.serialization.venue_types_serialize import VenueTypeListResponseModel
from pcapi.routes.serialization.venue_types_serialize import VenueTypeResponseModel
from pcapi.serialization.decorator import spectree_serialize

from . import blueprint


@private_api.route("/venue-types", methods=["GET"])
@login_required
@spectree_serialize(response_model=VenueTypeListResponseModel, api=blueprint.pro_private_schema)
def get_venue_types() -> VenueTypeListResponseModel:
    venue_types = [
        VenueTypeResponseModel(id=code_id, label=label)
        for code_id, label in offerers_models.VENUE_TYPE_CODE_MAPPING.items()
    ]
    return VenueTypeListResponseModel(__root__=venue_types)
