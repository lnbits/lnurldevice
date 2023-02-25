import json
from sqlite3 import Row
from typing import List, Optional

from lnurl.types import LnurlPayMetadata
from pydantic import BaseModel, Json


class LnurldeviceSwitch(BaseModel):
    amount: float = 0.0
    duration: int = 0
    pin: int = 0
    lnurl: Optional[str]


class CreateLnurldevice(BaseModel):
    title: str
    wallet: str
    currency: str
    device: str
    profit: float
    switches: Optional[List[LnurldeviceSwitch]]


class Lnurldevice(BaseModel):
    id: str
    key: str
    title: str
    wallet: str
    profit: float
    currency: str
    device: str
    switches: Optional[Json[List[LnurldeviceSwitch]]]
    timestamp: str

    @classmethod
    def from_row(cls, row: Row) -> "Lnurldevice":
        return cls(**dict(row))

    @property
    def lnurlpay_metadata(self) -> LnurlPayMetadata:
        return LnurlPayMetadata(json.dumps([["text/plain", self.title]]))

    # def switches(self, req: Request) -> List:
    #     switches = []
    #     if self.profit1 > 0:
    #         url = req.url_for("lnurldevice.lnurl_v1_params", device_id=self.id)
    #         switches.append(
    #             [
    #                 str(self.pin1),
    #                 str(self.profit1),
    #                 str(self.amount1),
    #                 lnurl_encode(
    #                     url
    #                     + "?gpio="
    #                     + str(self.pin1)
    #                     + "&profit="
    #                     + str(self.profit1)
    #                     + "&amount="
    #                     + str(self.amount1)
    #                 ),
    #             ]
    #         )
    #     return switches


class LnurldevicePayment(BaseModel):
    id: str
    deviceid: str
    payhash: str
    payload: str
    pin: int
    sats: int
    timestamp: str

    @classmethod
    def from_row(cls, row: Row) -> "LnurldevicePayment":
        return cls(**dict(row))
