import logging

from pcapi import settings
from pcapi.core.offerers.factories import ApiKeyFactory


logger = logging.getLogger(__name__)


def create_industrial_pro_users_api_keys(offerers_by_name):  # type: ignore [no-untyped-def]
    """Create api_keys with shape : {env}_{offererId}_clearSecret{offererId} ex: 'testing_12_clearSecret12'"""
    logger.info("create_industrial_pro_users_api_keys")

    for offerer in offerers_by_name.items():
        ApiKeyFactory(
            offerer=offerer[1], prefix=f"{settings.ENV}_{offerer[1].id}", secret=f"clearSecret{offerer[1].id}"
        )

    logger.info("created %d offerers with api key", len(offerers_by_name))
