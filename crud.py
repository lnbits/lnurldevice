import json
from typing import List, Optional

import shortuuid
from fastapi import Request
from lnurl import encode as lnurl_encode

from lnbits.helpers import urlsafe_short_hash

from . import db
from .models import CreateLnurldevice, Lnurldevice, LnurldevicePayment
from loguru import logger

async def create_lnurldevice(data: CreateLnurldevice, req: Request) -> Lnurldevice:
    if data.device == "pos" or data.device == "atm":
        lnurldevice_id = shortuuid.uuid()[:5]
    else:
        lnurldevice_id = urlsafe_short_hash()
    lnurldevice_key = urlsafe_short_hash()

    if data.switches:
        url = req.url_for("lnurldevice.lnurl_v2_params", device_id=lnurldevice_id)
        for _switch in data.switches:
            _switch.lnurl = lnurl_encode(
                str(url)
                + f"?pin={_switch.pin}"
                + f"&amount={_switch.amount}"
                + f"&duration={_switch.duration}"
                + f"&variable={_switch.variable}"
                + f"&comment={_switch.comment}"
                + f"&disabletime=0"
            )

    await db.execute(
        "INSERT INTO lnurldevice.lnurldevice (id, key, title, wallet, profit, currency, device, switches) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            lnurldevice_id,
            lnurldevice_key,
            data.title,
            data.wallet,
            data.profit,
            data.currency,
            data.device,
            json.dumps(data.switches, default=lambda x: x.dict()),
        ),
    )

    device = await get_lnurldevice(lnurldevice_id, req)
    assert device, "Lnurldevice was created but could not be retrieved"
    return device


async def update_lnurldevice(
    lnurldevice_id: str, data: CreateLnurldevice, req: Request
) -> Lnurldevice:

    if data.switches:
        url = req.url_for("lnurldevice.lnurl_v2_params", device_id=lnurldevice_id)
        for _switch in data.switches:
            _switch.lnurl = lnurl_encode(
                str(url)
                + f"?pin={_switch.pin}"
                + f"&amount={_switch.amount}"
                + f"&duration={_switch.duration}"
                + f"&variable={_switch.variable}"
                + f"&comment={_switch.comment}"
            )

    await db.execute(
        """
        UPDATE lnurldevice.lnurldevice SET
            title = ?,
            wallet = ?,
            profit = ?,
            currency = ?,
            device = ?,
            switches = ?
        WHERE id = ?
        """,
        (
            data.title,
            data.wallet,
            data.profit,
            data.currency,
            data.device,
            json.dumps(data.switches, default=lambda x: x.dict()),
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
    if device.switches:
        url = req.url_for("lnurldevice.lnurl_v2_params", device_id=device.id)
        for _switch in device.switches:
            _switch.lnurl = lnurl_encode(
                str(url)
                + f"?pin={_switch.pin}"
                + f"&amount={_switch.amount}"
                + f"&duration={_switch.duration}"
                + f"&variable={_switch.variable}"
                + f"&comment={_switch.comment}"
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

    # this is needed for backwards compabtibility, before the LNURL were cached inside db
    devices = [Lnurldevice(**row) for row in rows]

    for device in devices:
        if device.switches:
            url = req.url_for("lnurldevice.lnurl_v2_params", device_id=device.id)
            for _switch in device.switches:
                _switch.lnurl = lnurl_encode(
                    str(url)
                    + f"?pin={_switch.pin}"
                    + f"&amount={_switch.amount}"
                    + f"&duration={_switch.duration}"
                    + f"&variable={_switch.variable}"
                    + f"&comment={_switch.comment}"
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
