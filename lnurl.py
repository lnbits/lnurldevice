import base64
import hmac
from http import HTTPStatus
from io import BytesIO

from embit import compact
from fastapi import HTTPException, Query, Request
from lnbits import bolt11
from lnbits.core.services import create_invoice
from lnbits.core.views.api import pay_invoice
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis

from . import lnurldevice_ext
from .crud import (
    create_lnurldevicepayment,
    get_lnurldevice,
    get_lnurldevicepayment,
    update_lnurldevicepayment,
)


def xor_decrypt(key, blob):
    s = BytesIO(blob)
    variant = s.read(1)[0]
    if variant != 1:
        raise RuntimeError("Not implemented")
    # reading nonce
    l = s.read(1)[0]
    nonce = s.read(l)
    if len(nonce) != l:
        raise RuntimeError("Missing nonce bytes")
    if l < 8:
        raise RuntimeError("Nonce is too short")

    # reading payload
    l = s.read(1)[0]
    payload = s.read(l)
    if len(payload) > 32:
        raise RuntimeError("Payload is too long for this encryption method")
    if len(payload) != l:
        raise RuntimeError("Missing payload bytes")
    hmacval = s.read()
    expected = hmac.new(
        key, b"Data:" + blob[: -len(hmacval)], digestmod="sha256"
    ).digest()
    if len(hmacval) < 8:
        raise RuntimeError("HMAC is too short")
    if hmacval != expected[: len(hmacval)]:
        raise RuntimeError("HMAC is invalid")
    secret = hmac.new(key, b"Round secret:" + nonce, digestmod="sha256").digest()
    payload = bytearray(payload)
    for i in range(len(payload)):
        payload[i] = payload[i] ^ secret[i]
    s = BytesIO(payload)
    pin = compact.read_from(s)
    amount_in_cent = compact.read_from(s)
    return str(pin), amount_in_cent


@lnurldevice_ext.get(
    "/api/v1/lnurl/{device_id}",
    status_code=HTTPStatus.OK,
    name="lnurldevice.lnurl_v1_params",
)
async def lnurl_v1_params(
    request: Request,
    device_id: str = Query(None),
    p: str = Query(None),
    atm: str = Query(None),
    gpio: str = Query(None),
    profit: str = Query(None),
    amount: str = Query(None),
):
    return await lnurl_params(request, device_id, p, atm, gpio, profit, amount)


@lnurldevice_ext.get(
    "/api/v2/lnurl/{device_id}",
    status_code=HTTPStatus.OK,
    name="lnurldevice.lnurl_v2_params",
)
async def lnurl_v2_params(
    request: Request,
    device_id: str = Query(None),
    p: str = Query(None),
    atm: str = Query(None),
    pin: str = Query(None),
    amount: str = Query(None),
    duration: str = Query(None),
):
    return await lnurl_params(request, device_id, p, atm, pin, amount, duration)


async def lnurl_params(
    request: Request,
    device_id: str,
    p: str,
    atm: str,
    pin: str,
    amount: str,
    duration: str,
):
    device = await get_lnurldevice(device_id, request)
    if not device:
        return {
            "status": "ERROR",
            "reason": f"lnurldevice {device_id} not found on this server",
        }

    amount_in_cent = 0

    if device.device == "switch":
        price_msat = (
            await fiat_amount_as_satoshis(float(amount), device.currency)
            if device.currency != "sat"
            else amount_in_cent
        ) * 1000

        # Check they're not trying to trick the switch!
        check = False
        if device.switches:
            for switch in device.switches:
                if (
                    switch.pin == int(pin)
                    and switch.amount == float(amount)
                    and switch.duration == int(duration)
                ):
                    check = True
                    continue
        if not check:
            return {"status": "ERROR", "reason": "Switch params wrong"}

        lnurldevicepayment = await create_lnurldevicepayment(
            deviceid=device.id,
            payload=duration,
            sats=price_msat,
            pin=pin,
            payhash="bla",
        )
        if not lnurldevicepayment:
            return {"status": "ERROR", "reason": "Could not create payment."}

        return {
            "tag": "payRequest",
            "callback": request.url_for(
                "lnurldevice.lnurl_callback", paymentid=lnurldevicepayment.id
            ),
            "minSendable": price_msat,
            "maxSendable": price_msat,
            "metadata": device.lnurlpay_metadata,
        }

    if len(p) % 4 > 0:
        p += "=" * (4 - (len(p) % 4))

    data = base64.urlsafe_b64decode(p)
    try:
        pin, amount_in_cent = xor_decrypt(device.key.encode(), data)
    except Exception as exc:
        return {"status": "ERROR", "reason": str(exc)}

    price_msat = (
        await fiat_amount_as_satoshis(float(amount_in_cent) / 100, device.currency)
        if device.currency != "sat"
        else amount_in_cent
    ) * 1000

    if atm:
        if device.device != "atm":
            return {"status": "ERROR", "reason": "Not ATM device."}
        price_msat = int(price_msat * (1 - (device.profit / 100)) / 1000)
        try:
            lnurldevicepayment = await create_lnurldevicepayment(
                deviceid=device.id,
                payload=p,
                sats=price_msat * 1000,
                pin=pin,
                payhash="payment_hash",
            )
        except:
            return {"status": "ERROR", "reason": "Could not create ATM payment."}
        if not lnurldevicepayment:
            return {"status": "ERROR", "reason": "Could not create ATM payment."}
        return {
            "tag": "withdrawRequest",
            "callback": request.url_for(
                "lnurldevice.lnurl_callback", paymentid=lnurldevicepayment.id
            ),
            "k1": p,
            "minWithdrawable": price_msat * 1000,
            "maxWithdrawable": price_msat * 1000,
            "defaultDescription": device.title,
        }
    price_msat = int(price_msat * ((device.profit / 100) + 1) / 1000)

    lnurldevicepayment = await create_lnurldevicepayment(
        deviceid=device.id,
        payload=p,
        sats=price_msat * 1000,
        pin=pin,
        payhash="payment_hash",
    )
    if not lnurldevicepayment:
        return {"status": "ERROR", "reason": "Could not create payment."}
    return {
        "tag": "payRequest",
        "callback": request.url_for(
            "lnurldevice.lnurl_callback", paymentid=lnurldevicepayment.id
        ),
        "minSendable": price_msat * 1000,
        "maxSendable": price_msat * 1000,
        "metadata": device.lnurlpay_metadata,
    }


@lnurldevice_ext.get(
    "/api/v1/lnurl/cb/{paymentid}",
    status_code=HTTPStatus.OK,
    name="lnurldevice.lnurl_callback",
)
async def lnurl_callback(
    request: Request,
    paymentid: str = Query(None),
    pr: str = Query(None),
    k1: str = Query(None),
):
    lnurldevicepayment = await get_lnurldevicepayment(paymentid)
    if not lnurldevicepayment:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnurldevicepayment not found."
        )
    device = await get_lnurldevice(lnurldevicepayment.deviceid, request)
    if not device:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnurldevice not found."
        )
    if device.device == "atm":
        if lnurldevicepayment.payload == lnurldevicepayment.payhash:
            return {"status": "ERROR", "reason": "Payment already claimed"}
        if not pr:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="No payment request"
            )
        invoice = bolt11.decode(pr)
        if not invoice.payment_hash:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN, detail="Not valid payment request"
            )
        else:
            if lnurldevicepayment.payload != k1:
                return {"status": "ERROR", "reason": "Bad K1"}
            if lnurldevicepayment.payhash != "payment_hash":
                return {"status": "ERROR", "reason": "Payment already claimed"}

            lnurldevicepayment_updated = await update_lnurldevicepayment(
                lnurldevicepayment_id=paymentid, payhash=lnurldevicepayment.payload
            )
            assert lnurldevicepayment_updated
            await pay_invoice(
                wallet_id=device.wallet,
                payment_request=pr,
                max_sat=int(lnurldevicepayment_updated.sats / 1000),
                extra={"tag": "withdraw"},
            )
            return {"status": "OK"}
    if device.device == "switch":
        payment_hash, payment_request = await create_invoice(
            wallet_id=device.wallet,
            amount=int(lnurldevicepayment.sats / 1000),
            memo=device.id + " PIN " + str(lnurldevicepayment.pin),
            unhashed_description=device.lnurlpay_metadata.encode(),
            extra={
                "tag": "Switch",
                "pin": str(lnurldevicepayment.pin),
                "amount": str(lnurldevicepayment.payload),
                "id": paymentid,
            },
        )

        lnurldevicepayment = await update_lnurldevicepayment(
            lnurldevicepayment_id=paymentid, payhash=payment_hash
        )
        return {
            "pr": payment_request,
            "routes": [],
        }

    payment_hash, payment_request = await create_invoice(
        wallet_id=device.wallet,
        amount=int(lnurldevicepayment.sats / 1000),
        memo=device.title,
        unhashed_description=device.lnurlpay_metadata.encode(),
        extra={"tag": "PoS"},
    )
    lnurldevicepayment = await update_lnurldevicepayment(
        lnurldevicepayment_id=paymentid, payhash=payment_hash
    )

    return {
        "pr": payment_request,
        "successAction": {
            "tag": "url",
            "description": "Check the attached link",
            "url": request.url_for("lnurldevice.displaypin", paymentid=paymentid),
        },
        "routes": [],
    }
