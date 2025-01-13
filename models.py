import json
from typing import List, Optional, Union

from lnurl.types import LnurlPayMetadata
from pydantic import BaseModel, Json


class LnurldeviceExtra(BaseModel):
    description: str = ""
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
    extra: Optional[Union[List[LnurldeviceExtra], str]]


class Lnurldevice(BaseModel):
    id: str
    key: str
    title: str
    wallet: str
    profit: float
    currency: str
    device: str
    extra: Optional[Union[Json[List[LnurldeviceExtra]], str]]

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


class Lnurlencode(BaseModel):
    url: str
