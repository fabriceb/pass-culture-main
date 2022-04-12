from pcapi.routes.serialization import BaseModel


class Role(BaseModel):
    name: str
    permissions: list[str]
