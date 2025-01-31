from apscheduler.schedulers.blocking import BlockingScheduler
from sentry_sdk import set_tag

from pcapi.local_providers.provider_manager import synchronize_data_for_provider
from pcapi.models.feature import FeatureToggle
from pcapi.scheduled_tasks import utils
from pcapi.scheduled_tasks.decorators import cron_context
from pcapi.scheduled_tasks.decorators import cron_require_feature
from pcapi.scheduled_tasks.decorators import log_cron_with_transaction
from pcapi.utils.blueprint import Blueprint


blueprint = Blueprint(__name__, __name__)

# FIXME (jsdupuis, 2022-03-15) : every @cron in this module functions are to be deleted
#  when cron will be managed by the infrastructure rather than by the app


@cron_context
@log_cron_with_transaction
@cron_require_feature(FeatureToggle.SYNCHRONIZE_TITELIVE_PRODUCTS)
def synchronize_titelive_things():  # type: ignore [no-untyped-def]
    synchronize_data_for_provider("TiteLiveThings")


@cron_context
@log_cron_with_transaction
@cron_require_feature(FeatureToggle.SYNCHRONIZE_TITELIVE_PRODUCTS_DESCRIPTION)
def synchronize_titelive_thing_descriptions():  # type: ignore [no-untyped-def]
    synchronize_data_for_provider("TiteLiveThingDescriptions")


@cron_context
@log_cron_with_transaction
@cron_require_feature(FeatureToggle.SYNCHRONIZE_TITELIVE_PRODUCTS_THUMBS)
def synchronize_titelive_thing_thumbs():  # type: ignore [no-untyped-def]
    synchronize_data_for_provider("TiteLiveThingThumbs")


# FIXME (jsdupuis, 2022-03-10) : to be deleted when cron will be managed by the infrastructure rather than by the app
@blueprint.cli.command("titelive_clock")
def titelive_clock():  # type: ignore [no-untyped-def]
    set_tag("pcapi.app_type", "titelive_clock")
    scheduler = BlockingScheduler()
    utils.activate_sentry(scheduler)

    scheduler.add_job(synchronize_titelive_things, "cron", day="*", hour="1")

    scheduler.add_job(synchronize_titelive_thing_descriptions, "cron", day="*", hour="2")

    scheduler.add_job(synchronize_titelive_thing_thumbs, "cron", day="*", hour="3")

    scheduler.start()
