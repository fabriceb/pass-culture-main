from flask import current_app

from pcapi.core.search import testing

from .algolia import AlgoliaBackend


class FakeClient:
    def __init__(self, key):  # type: ignore [no-untyped-def]
        self.key = key

    def save_objects(self, objects):  # type: ignore [no-untyped-def]
        for obj in objects:
            testing.search_store[self.key][obj["objectID"]] = obj

    def delete_objects(self, object_ids):  # type: ignore [no-untyped-def]
        for object_id in object_ids:
            testing.search_store[self.key].pop(object_id, None)

    def clear_objects(self):  # type: ignore [no-untyped-def]
        testing.search_store[self.key] = {}


class TestingBackend(AlgoliaBackend):
    """A backend to be used by automated tests.

    We subclass a real-looking backend to be as close as possible to
    what we have in production. Only the communication with the
    external search service is faked.
    """

    def __init__(self):  # type: ignore [no-untyped-def] # pylint: disable=super-init-not-called
        self.algolia_offers_client = FakeClient("offers")
        self.algolia_venues_client = FakeClient("venues")
        self.algolia_collective_offers_client = FakeClient("collective-offers")
        self.algolia_collective_offers_templates_client = FakeClient("collective-offers-templates")
        self.redis_client = current_app.redis_client
