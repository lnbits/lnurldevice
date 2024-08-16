import json
from typing import List, Optional
import shortuuid
from fastapi import Request
from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash
from lnurl import encode as lnurl_encode

from lnbits.helpers import urlsafe_short_hash
from .models import CreateLnurldevice, Lnurldevice, LnurldevicePayment

db = Database("ext_lnurldevice")


async def create_lnurldevice(data: CreateLnurldevice, req: Request) -> Lnurldevice:
    if data.device == "pos" or data.device == "atm":
        lnurldevice_id = shortuuid.uuid()[:5]
    else:
        lnurldevice_id = urlsafe_short_hash()
    lnurldevice_key = urlsafe_short_hash()

    if isinstance(data.extra, list):
        url = req.url_for("lnurldevice.lnurl_v2_params", device_id=lnurldevice_id)
        for _extra in data.extra:
            _extra.lnurl = lnurl_encode(
                str(url)
                + f"?pin={_extra.pin}"
                + f"&amount={_extra.amount}"
                + f"&duration={_extra.duration}"
                + f"&variable={_extra.variable}"
                + f"&comment={_extra.comment}"
                + f"&disabletime=0"
            )

    await db.execute(
        "INSERT INTO lnurldevice.lnurldevice (id, key, title, wallet, profit, currency, device, extra) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            lnurldevice_id,
            lnurldevice_key,
            data.title,
            data.wallet,
            data.profit,
            data.currency,
            data.device,
            json.dumps(data.extra, default=lambda x: x.dict()) if data.extra != "boltz" else data.extra,
        ),
    )

    device = await get_lnurldevice(lnurldevice_id, req)
    assert device, "Lnurldevice was created but could not be retrieved"
    return device

async def update_lnurldevice(
    lnurldevice_id: str, data: CreateLnurldevice, req: Request
) -> Lnurldevice:
    if isinstance(data.extra, list):
        url = req.url_for("lnurldevice.lnurl_v2_params", device_id=lnurldevice_id)
        for _extra in data.extra:
            _extra.lnurl = lnurl_encode(
                str(url)
                + f"?pin={_extra.pin}"
                + f"&amount={_extra.amount}"
                + f"&duration={_extra.duration}"
                + f"&variable={_extra.variable}"
                + f"&comment={_extra.comment}"
            )

    await db.execute(
        """
        UPDATE lnurldevice.lnurldevice SET
            title = ?,
            wallet = ?,
            profit = ?,
            currency = ?,
            device = ?,
            extra = ?
        WHERE id = ?
        """,
        (
            data.title,
            data.wallet,
            data.profit,
            data.currency,
            data.device,
            json.dumps(data.extra, default=lambda x: x.dict()) if data.extra != "boltz" else data.extra,
            lnurldevice_id,
        ),
    )
    device = await get_lnurldevice(lnurldevice_id, req)
    assert device, "Lnurldevice was updated but could not be retrieved"
    return device

async def get_lnurldevice(lnurldevice_id: str, req: Request) -> Optional[Lnurldevice]:
    row = await db.fetchone(
        "SELECT * FROM lnurldevice.lnurldevice WHERE id = ?", (lnurldevice_id,)
    )
    if not row:
        return None

    device = Lnurldevice(**row)

    # this is needed for backwards compabtibility, before the LNURL were cached inside db
    if isinstance(device.extra, list):
        url = req.url_for("lnurldevice.lnurl_v2_params", device_id=device.id)
        for _extra in device.extra:
            _extra.lnurl = lnurl_encode(
                str(url)
                + f"?pin={_extra.pin}"
                + f"&amount={_extra.amount}"
                + f"&duration={_extra.duration}"
                + f"&variable={_extra.variable}"
                + f"&comment={_extra.comment}"
            )

    return device


async def get_lnurldevices(wallet_ids: List[str], req: Request) -> List[Lnurldevice]:

    q = ",".join(["?"] * len(wallet_ids))
    rows = await db.fetchall(
        f"""
        SELECT * FROM lnurldevice.lnurldevice WHERE wallet IN ({q})
        ORDER BY id
        """,
        (*wallet_ids,),
    )

    # this is needed for backwards compabtibility,
    # before the LNURL were cached inside db
    devices = [Lnurldevice(**row) for row in rows]

    for device in devices:
        if isinstance(device.extra, list):
            url = req.url_for("lnurldevice.lnurl_v2_params", device_id=device.id)
            for _extra in device.extra:
                _extra.lnurl = lnurl_encode(
                    str(url)
                    + f"?pin={_extra.pin}"
                    + f"&amount={_extra.amount}"
                    + f"&duration={_extra.duration}"
                    + f"&variable={_extra.variable}"
                    + f"&comment={_extra.comment}"
                )

    return devices

async def delete_lnurldevice(lnurldevice_id: str) -> None:
    await db.execute(
        "DELETE FROM lnurldevice.lnurldevice WHERE id = ?", (lnurldevice_id,)
    )

async def create_lnurldevicepayment(
    deviceid: str,
    payload: Optional[str] = None,
    pin: Optional[str] = None,
    payhash: Optional[str] = None,
    sats: Optional[int] = 0,
) -> LnurldevicePayment:

    # TODO: ben what is this for?
    # if device.device == "atm":
    #     lnurldevicepayment_id = shortuuid.uuid(name=payload)
    # else:

    lnurldevicepayment_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO lnurldevice.lnurldevicepayment (
            id,
            deviceid,
            payload,
            pin,
            payhash,
            sats
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (lnurldevicepayment_id, deviceid, payload, pin, payhash, sats),
    )
    dpayment = await get_lnurldevicepayment(lnurldevicepayment_id)
    assert dpayment, "Couldnt retrieve newly created LnurldevicePayment"
    return dpayment

async def update_lnurldevicepayment(
    lnurldevicepayment_id: str, **kwargs
) -> LnurldevicePayment:
    q = ", ".join([f"{field[0]} = ?" for field in kwargs.items()])
    await db.execute(
        f"UPDATE lnurldevice.lnurldevicepayment SET {q} WHERE id = ?",
        (*kwargs.values(), lnurldevicepayment_id),
    )
    dpayment = await get_lnurldevicepayment(lnurldevicepayment_id)
    assert dpayment, "Couldnt retrieve update LnurldevicePayment"
    return dpayment

async def get_lnurldevicepayment(
    lnurldevicepayment_id: str,
) -> Optional[LnurldevicePayment]:
    row = await db.fetchone(
        "SELECT * FROM lnurldevice.lnurldevicepayment WHERE id = ?",
        (lnurldevicepayment_id,),
    )
    return LnurldevicePayment(**row) if row else None

async def get_lnurldevicepayments(lnurldevice_ids: List[str]) -> List[LnurldevicePayment]:
    q = ",".join(["?"] * len(lnurldevice_ids))
    rows = await db.fetchall(
        f"""
        SELECT * FROM lnurldevice.lnurldevicepayment WHERE deviceid IN ({q})
        ORDER BY id
        """,
        (*lnurldevice_ids,),
    )
    return [LnurldevicePayment(**row) for row in rows]

async def get_lnurldevicepayment_by_p(
    p: str,
) -> Optional[LnurldevicePayment]:
    row = await db.fetchone(
        "SELECT * FROM lnurldevice.lnurldevicepayment WHERE payhash = ?",
        (p,),
    )
    return LnurldevicePayment(**row) if row else None


async def get_lnurlpayload(
    lnurldevicepayment_payload: str,
) -> Optional[LnurldevicePayment]:
    row = await db.fetchone(
        "SELECT * FROM lnurldevice.lnurldevicepayment WHERE payload = ?",
        (lnurldevicepayment_payload,),
    )
    return LnurldevicePayment(**row) if row else None

async def get_recent_lnurldevicepayment(
    p: str,
) -> Optional[LnurldevicePayment]:
    row = await db.fetchone(
        "SELECT * FROM lnurldevice.lnurldevicepayment WHERE payload = ? ORDER BY timestamp DESC LIMIT 1",
        (p,),
    )
    return LnurldevicePayment(**row) if row else None

async def delete_atm_payment_link(atm_id: str) -> None:
    await db.execute(
        "DELETE FROM lnurldevice.lnurldevicepayment WHERE id = ?", (atm_id,)
    )
