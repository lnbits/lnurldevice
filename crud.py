from typing import List, Optional
import json

import shortuuid

from lnbits.helpers import urlsafe_short_hash

from . import db
from .models import CreateLnurldevice, Lnurldevice, LnurldevicePayment


async def create_lnurldevice(data: CreateLnurldevice) -> Lnurldevice:
    if data.device == "pos" or data.device == "atm":
        lnurldevice_id = shortuuid.uuid()[:5]
    else:
        lnurldevice_id = urlsafe_short_hash()
    lnurldevice_key = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO lnurldevice.lnurldevice (
            id,
            key,
            title,
            wallet,
            profit,
            currency,
            device,
            switches
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
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
    device = await get_lnurldevice(lnurldevice_id)
    assert device, "Lnurldevice was created but could not be retrieved"
    return device


async def update_lnurldevice(lnurldevice_id: str, data: CreateLnurldevice) -> Lnurldevice:
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
    row = await db.fetchone(
        "SELECT * FROM lnurldevice.lnurldevice WHERE id = ?", (lnurldevice_id,)
    )
    assert row, "Lnurldevice could no retrieved updated model"
    return Lnurldevice(**row)


async def get_lnurldevice(lnurldevice_id: str) -> Optional[Lnurldevice]:
    row = await db.fetchone(
        "SELECT * FROM lnurldevice.lnurldevice WHERE id = ?", (lnurldevice_id,)
    )
    return Lnurldevice(**row) if row else None


async def get_lnurldevices(wallet_ids: List[str]) -> List[Lnurldevice]:
    q = ",".join(["?"] * len(wallet_ids))
    rows = await db.fetchall(
        f"""
        SELECT * FROM lnurldevice.lnurldevice WHERE wallet IN ({q})
        ORDER BY id
        """,
        (*wallet_ids,),
    )

    return [Lnurldevice(**row) for row in rows]


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
    device = await get_lnurldevice(deviceid)
    assert device
    if device.device == "atm":
        lnurldevicepayment_id = shortuuid.uuid(name=payload)
    else:
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


async def update_lnurldevicepayment(lnurldevicepayment_id: str, **kwargs) -> LnurldevicePayment:
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


async def get_lnurlpayload(
    lnurldevicepayment_payload: str,
) -> Optional[LnurldevicePayment]:
    row = await db.fetchone(
        "SELECT * FROM lnurldevice.lnurldevicepayment WHERE payload = ?",
        (lnurldevicepayment_payload,),
    )
    return LnurldevicePayment(**row) if row else None
