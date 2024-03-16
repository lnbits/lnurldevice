import json
from sqlite3 import Row
from typing import List, Optional

from lnurl.types import LnurlPayMetadata
from pydantic import BaseModel, Json


class LnurldeviceSwitch(BaseModel):
    amount: float = 0.0
    duration: int = 0
    pin: int = 0
    comment: Optional[bool] = False
    variable: Optional[bool] = False
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
