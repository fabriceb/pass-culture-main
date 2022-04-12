from pcapi.core.permissions.models import Role


def list_roles() -> list[Role]:
    return Role.query.all()
