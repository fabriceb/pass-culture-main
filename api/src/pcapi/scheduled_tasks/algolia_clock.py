from apscheduler.schedulers.blocking import BlockingScheduler
from sentry_sdk import set_tag

from pcapi import settings
from pcapi.core import search
import pcapi.core.educational.api as educational_api
import pcapi.core.offers.api as offers_api
from pcapi.scheduled_tasks import utils
from pcapi.scheduled_tasks.decorators import cron_context
from pcapi.scheduled_tasks.decorators import log_cron_with_transaction
from pcapi.utils.blueprint import Blueprint


blueprint = Blueprint(__name__, __name__)

# FIXME (jsdupuis, 2022-03-15) : every @cron in this module functions are to be deleted
#  when cron will be managed by the infrastructure rather than by the app


@cron_context
@log_cron_with_transaction
def index_offers_in_algolia_by_offer():  # type: ignore [no-untyped-def]
    search.index_offers_in_queue()


@cron_context
@log_cron_with_transaction
def index_offers_in_algolia_by_venue():  # type: ignore [no-untyped-def]
    search.index_offers_of_venues_in_queue()


@cron_context
@log_cron_with_transaction
def index_collective_offers():  # type: ignore [no-untyped-def]
    search.index_collective_offers_in_queue()


@cron_context
@log_cron_with_transaction
def index_collective_offer_templates():  # type: ignore [no-untyped-def]
    search.index_collective_offers_templates_in_queue()


@cron_context
@log_cron_with_transaction
def delete_expired_offers_in_algolia():  # type: ignore [no-untyped-def]
    offers_api.unindex_expired_offers()


@cron_context
@log_cron_with_transaction
def delete_expired_collective_offers_in_algolia():  # type: ignore [no-untyped-def]
    educational_api.unindex_expired_collective_offers()


@cron_context
@log_cron_with_transaction
def index_offers_in_error_in_algolia_by_offer():  # type: ignore [no-untyped-def]
    search.index_offers_in_queue(from_error_queue=True)


@cron_context
@log_cron_with_transaction
def index_collective_offers_in_error():  # type: ignore [no-untyped-def]
    search.index_collective_offers_in_queue(from_error_queue=True)


@cron_context
@log_cron_with_transaction
def index_collective_offers_templates_in_error():  # type: ignore [no-untyped-def]
    search.index_collective_offers_templates_in_queue(from_error_queue=True)


@cron_context
@log_cron_with_transaction
def index_venues():  # type: ignore [no-untyped-def]
    search.index_venues_in_queue()


@cron_context
@log_cron_with_transaction
def index_venues_in_error():  # type: ignore [no-untyped-def]
    search.index_venues_in_queue(from_error_queue=True)


# FIXME (jsdupuis, 2022-03-10) : to be deleted when cron will be managed by the infrastructure rather than by the app
@blueprint.cli.command("algolia_clock")
def algolia_clock():  # type: ignore [no-untyped-def]
    set_tag("pcapi.app_type", "algolia_clock")
    scheduler = BlockingScheduler()
    utils.activate_sentry(scheduler)

    # ---- Offers ----- #

    scheduler.add_job(
        index_offers_in_algolia_by_offer,
        "cron",
        minute=settings.ALGOLIA_CRON_INDEXING_OFFERS_BY_OFFER_FREQUENCY,
        max_instances=4,
    )

    scheduler.add_job(
        index_offers_in_algolia_by_venue,
        "cron",
        minute=settings.ALGOLIA_CRON_INDEXING_OFFERS_BY_VENUE_PROVIDER_FREQUENCY,
    )

    scheduler.add_job(delete_expired_offers_in_algolia, "cron", day="*", hour="1")

    scheduler.add_job(
        index_offers_in_error_in_algolia_by_offer,
        "cron",
        minute=settings.ALGOLIA_CRON_INDEXING_OFFERS_IN_ERROR_BY_OFFER_FREQUENCY,
    )

    # ---- Venues ----- #

    scheduler.add_job(
        index_venues,
        "cron",
        minute=settings.CRON_INDEXING_VENUES_FREQUENCY,
    )

    scheduler.add_job(
        index_venues_in_error,
        "cron",
        minute=settings.CRON_INDEXING_VENUES_IN_ERROR_FREQUENCY,
    )

    # ---- Collective Offers and Templates----- #

    scheduler.add_job(
        index_collective_offers,
        "cron",
        minute=settings.CRON_INDEXING_COLLECTIVE_OFFERS_FREQUENCY,
    )
    scheduler.add_job(
        index_collective_offer_templates,
        "cron",
        minute=settings.CRON_INDEXING_COLLECTIVE_OFFERS_TEMPLATES_FREQUENCY,
    )

    scheduler.add_job(
        index_collective_offers_in_error,
        "cron",
        minute=settings.CRON_INDEXING_COLLECTIVE_OFFERS_IN_ERROR_FREQUENCY,
    )
    scheduler.add_job(
        index_collective_offers_templates_in_error,
        "cron",
        minute=settings.CRON_INDEXING_COLLECTIVE_OFFERS_TEMPLATES_IN_ERROR_FREQUENCY,
    )

    scheduler.add_job(delete_expired_collective_offers_in_algolia, "cron", day="*", hour="1")

    scheduler.start()
