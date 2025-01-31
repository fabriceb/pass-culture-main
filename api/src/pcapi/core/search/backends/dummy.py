from flask import current_app

from .algolia import AlgoliaBackend


class FakeClient:
    def save_objects(self, objects):  # type: ignore [no-untyped-def]
        pass

    def delete_objects(self, object_ids):  # type: ignore [no-untyped-def]
        pass

    def clear_objects(self):  # type: ignore [no-untyped-def]
        pass


class DummyBackend(AlgoliaBackend):
    """A backend that does not communicate with the external search
    service.

    We subclass a real-looking backend to be as close as possible to
    what we have in production. Only the communication with the
    external search service is faked.

    Note that we still use Redis for the queue. We could implement all
    Redis-related functions as no-op, but it's not worth.
    """

    def __init__(self):  # type: ignore [no-untyped-def] # pylint: disable=super-init-not-called
        self.algolia_offers_client = FakeClient()
        self.algolia_venues_client = FakeClient()
        self.algolia_collective_offers_client = FakeClient()
        self.algolia_collective_offers_templates_client = FakeClient()
        self.redis_client = current_app.redis_client
