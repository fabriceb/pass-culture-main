import datetime

from pydantic import Field

from pcapi.routes.serialization import BaseModel


class ShowCDS(BaseModel):
    id: int
    is_cancelled: bool = Field(alias="canceled")
    is_deleted: bool = Field(alias="deleted")
    internet_remaining_place: int = Field(alias="internetremainingplace")
    showtime: datetime.datetime

    class Config:
        allow_population_by_field_name = True


class IdObjectCDS(BaseModel):
    id: int


class TicketSaleCDS(BaseModel):
    id: int
    cinemaid: str
    operationdate: str
    canceled: bool
    tariffid: IdObjectCDS
    showid: IdObjectCDS
    disabledperson: bool


class PaiementCDS(BaseModel):
    id: int
    amount: float
    paiementtypeid: IdObjectCDS


class CreateTransactionBodyCDS(BaseModel):
    cinemaid: str
    transactiondate: str
    canceled: bool
    ticketsaleCollection: list[TicketSaleCDS]
    paiementCollection: list[PaiementCDS]


class TicketResponseCDS(BaseModel):
    barcode: str


class CreateTransactionResponseCDS(BaseModel):
    id: int
    invoiceid: str
    tickets: list[TicketResponseCDS]
