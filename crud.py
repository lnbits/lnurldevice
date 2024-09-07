import json
from datetime import datetime
from typing import Optional

import shortuuid
from fastapi import Request
from lnbits.db import Database
from lnbits.helpers import insert_query, update_query, urlsafe_short_hash
from lnurl import encode as lnurl_encode

from .models import CreateLnurldevice, Lnurldevice, LnurldevicePayment

db = Database("ext_lnurldevice")


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
                + "&disabletime=0"
            )

    await db.execute(
        """
        INSERT INTO lnurldevice.lnurldevice
        (id, key, title, wallet, profit, currency, device, switches)
        VALUES (:id, :key, :title, :wallet, :profit, :currency, :device, :switches)
        """,
        {
            "id": lnurldevice_id,
            "key": lnurldevice_key,
            "title": data.title,
            "wallet": data.wallet,
            "profit": data.profit,
            "currency": data.currency,
            "device": data.device,
            "switches": json.dumps(data.switches, default=lambda x: x.dict()),
        },
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
            title = :title,
            wallet = :wallet,
            profit = :profit,
            currency = :currency,
            device = :device,
            switches = :switches,
        WHERE id = :id
        """,
        {
            "id": lnurldevice_id,
            "title": data.title,
            "wallet": data.wallet,
            "profit": data.profit,
            "currency": data.currency,
            "device": data.device,
            "switches": json.dumps(data.switches, default=lambda x: x.dict()),
        },
    )
    device = await get_lnurldevice(lnurldevice_id, req)
    assert device, "Lnurldevice was updated but could not be retrieved"
    return device


async def get_lnurldevice(lnurldevice_id: str, req: Request) -> Optional[Lnurldevice]:
    row = await db.fetchone(
        "SELECT * FROM lnurldevice.lnurldevice WHERE id = :id", {"id": lnurldevice_id}
    )
    if not row:
        return None

    device = Lnurldevice(**row)

    # this is needed for backwards compabtibility,
    # before the LNURL were cached inside db
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


async def get_lnurldevices(wallet_ids: list[str], req: Request) -> list[Lnurldevice]:

    q = ",".join([f"'{w}'" for w in wallet_ids])
    rows = await db.fetchall(
        f"SELECT * FROM lnurldevice.lnurldevice WHERE wallet IN ({q}) ORDER BY id",
    )

    # this is needed for backwards compabtibility,
    # before the LNURL were cached inside db
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
        "DELETE FROM lnurldevice.lnurldevice WHERE id = :id",
        {"id": lnurldevice_id},
    )


async def create_lnurldevicepayment(
    deviceid: str,
    payload: str,
    pin: int,
    payhash: str,
    sats: int,
) -> LnurldevicePayment:

    # TODO: ben what is this for?
    # if device.device == "atm":
    #     lnurldevicepayment_id = shortuuid.uuid(name=payload)
    # else:

    lnurldevicepayment_id = urlsafe_short_hash()
    payment = LnurldevicePayment(
        id=lnurldevicepayment_id,
        deviceid=deviceid,
        payload=payload,
        pin=pin,
        payhash=payhash,
        sats=sats,
        timestamp=datetime.now(),
    )
    await db.execute(
        insert_query("lnurldevice.lnurldevicepayment", payment),
        payment.dict(),
    )
    return payment


async def update_lnurldevicepayment(payment: LnurldevicePayment) -> LnurldevicePayment:
    await db.execute(
        update_query("lnurldevice.lnurldevicepayment", payment),
        payment.dict(),
    )
    return payment


async def get_lnurldevicepayment(
    lnurldevicepayment_id: str,
) -> Optional[LnurldevicePayment]:
    row = await db.fetchone(
        "SELECT * FROM lnurldevice.lnurldevicepayment WHERE id = :id",
        {"id": lnurldevicepayment_id},
    )
    return LnurldevicePayment(**row) if row else None


async def get_lnurldevicepayment_by_p(
    payment_hash: str,
) -> Optional[LnurldevicePayment]:
    row = await db.fetchone(
        "SELECT * FROM lnurldevice.lnurldevicepayment WHERE payhash = :hash",
        {"hash": payment_hash},
    )
    return LnurldevicePayment(**row) if row else None


async def get_lnurlpayload(payload: str) -> Optional[LnurldevicePayment]:
    row = await db.fetchone(
        "SELECT * FROM lnurldevice.lnurldevicepayment WHERE payload = :payload",
        {"payload": payload},
    )
    return LnurldevicePayment(**row) if row else None
