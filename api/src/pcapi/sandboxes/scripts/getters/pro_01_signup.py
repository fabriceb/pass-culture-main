from pcapi.core.offerers import factories as offerers_factories
from pcapi.core.users import factories as users_factories
from pcapi.sandboxes.scripts.utils.helpers import get_offerer_helper
from pcapi.sandboxes.scripts.utils.helpers import get_pro_helper


def get_existing_pro_user_with_offerer():  # type: ignore [no-untyped-def]
    user_offerer = offerers_factories.UserOffererFactory(
        user__validationToken=None,
    )
    return {"offerer": get_offerer_helper(user_offerer.offerer), "user": get_pro_helper(user_offerer.user)}


def get_existing_pro_not_validated_user_with_real_offerer():  # type: ignore [no-untyped-def]
    return {"user": get_pro_helper(users_factories.ProFactory())}
