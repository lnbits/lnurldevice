import base64
from http import HTTPStatus

import bolt11
from fastapi import APIRouter, Query, Request
from lnbits.core.crud import get_wallet
from lnbits.core.services import create_invoice
from lnbits.core.views.api import pay_invoice
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis

from .crud import (
    create_lnurldevicepayment,
    delete_atm_payment_link,
    get_lnurldevice,
    get_lnurldevicepayment,
    update_lnurldevicepayment,
)
from .helpers import register_atm_payment, xor_decrypt

lnurldevice_lnurl_router = APIRouter()


@lnurldevice_lnurl_router.get(
    "/api/v1/lnurl/{device_id}",
    status_code=HTTPStatus.OK,
    name="lnurldevice.lnurl_v1_params",
)
async def lnurl_v1_params(
    request: Request,
    device_id: str,
    p: str = Query(None),
    atm: str = Query(None),
    gpio: str = Query(None),
    profit: str = Query(None),
    amount: str = Query(None),
):
    return await lnurl_params(request, device_id, p, atm, gpio, profit, amount)


@lnurldevice_lnurl_router.get(
    "/api/v2/lnurl/{device_id}",
    status_code=HTTPStatus.OK,
    name="lnurldevice.lnurl_v2_params",
)
async def lnurl_v2_params(
    request: Request,
    device_id: str,
    p: str = Query(None),
    atm: str = Query(None),
    pin: str = Query(None),
    amount: str = Query(None),
    duration: str = Query(None),
    variable: bool = Query(None),
    comment: bool = Query(None),
):
    return await lnurl_params(
        request, device_id, p, atm, pin, amount, duration, variable, comment
    )


async def lnurl_params(
    request: Request,
    device_id: str,
    p: str,
    atm: str,
    pin: str,
    amount: str,
    duration: str,
    variable: bool = Query(None),
    comment: bool = Query(None),
):
    device = await get_lnurldevice(device_id, request)
    if not device:
        return {
            "status": "ERROR",
            "reason": f"lnurldevice {device_id} not found on this server",
        }

    if device.device == "switch":
        price_msat = int(
            (
                await fiat_amount_as_satoshis(float(amount), device.currency)
                if device.currency != "sat"
                else float(amount)
            )
            * 1000
        )

        # Check they're not trying to trick the switch!
        check = False
        if (
            device.extra
            and not isinstance(device.extra, str)
            and "atm" not in device.extra
        ):
            for extra in device.extra:
                if (
                    extra.pin == int(pin)
                    and extra.duration == int(duration)
                    and bool(extra.variable) == bool(variable)
                    and bool(extra.comment) == bool(comment)
                ):
                    check = True
                    continue
        if not check:
            return {"status": "ERROR", "reason": "Extra params wrong"}

        lnurldevicepayment = await create_lnurldevicepayment(
            deviceid=device.id,
            payload=duration,
            sats=price_msat,
            pin=pin,
            payhash="bla",
        )
        if not lnurldevicepayment:
            return {"status": "ERROR", "reason": "Could not create payment."}
        resp = {
            "tag": "payRequest",
            "callback": str(
                request.url_for(
                    "lnurldevice.lnurl_callback",
                    paymentid=lnurldevicepayment.id,
                )
            )
            + f"?variable={variable}",
            "minSendable": price_msat,
            "maxSendable": price_msat,
            "metadata": device.lnurlpay_metadata,
        }
        if comment:
            resp["commentAllowed"] = 1500
        if variable:
            resp["maxSendable"] = price_msat * 360
        return resp

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
    )
    if price_msat is None:
        return {"status": "ERROR", "reason": "Price fetch error."}

    if atm:
        lnurldevicepayment, price_msat = await register_atm_payment(device, p)
        if not lnurldevicepayment:
            return {"status": "ERROR", "reason": "Could not create ATM payment."}
        return {
            "tag": "withdrawRequest",
            "callback": str(
                request.url_for(
                    "lnurldevice.lnurl_callback", paymentid=lnurldevicepayment.id
                )
            ),
            "k1": p,
            "minWithdrawable": price_msat,
            "maxWithdrawable": price_msat,
            "defaultDescription": f"{device.title} ID: {lnurldevicepayment.id}",
        }
    price_msat = int(price_msat * ((device.profit / 100) + 1))

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
        "callback": str(
            request.url_for(
                "lnurldevice.lnurl_callback", paymentid=lnurldevicepayment.id
            )
        ),
        "minSendable": price_msat * 1000,
        "maxSendable": price_msat * 1000,
        "metadata": device.lnurlpay_metadata,
    }


@lnurldevice_lnurl_router.get(
    "/api/v1/lnurl/cb/{paymentid}",
    status_code=HTTPStatus.OK,
    name="lnurldevice.lnurl_callback",
)
async def lnurl_callback(
    request: Request,
    paymentid: str,
    variable: str = Query(None),
    amount: int = Query(None),
    comment: str = Query(None),
    pr: str = Query(None),
    k1: str = Query(None),
):
    lnurldevicepayment = await get_lnurldevicepayment(paymentid)
    if not lnurldevicepayment:
        return {"status": "ERROR", "reason": "lnurldevicepayment not found."}
    device = await get_lnurldevice(lnurldevicepayment.deviceid, request)
    if not device:
        await delete_atm_payment_link(paymentid)
        return {"status": "ERROR", "reason": "lnurldevice not found."}
    if device.device == "atm":
        if lnurldevicepayment.payload == lnurldevicepayment.payhash:
            await delete_atm_payment_link(paymentid)
            return {"status": "ERROR", "reason": "Payment already claimed"}
        if not pr:
            await delete_atm_payment_link(paymentid)
            return {"status": "ERROR", "reason": "No payment request."}
        invoice = bolt11.decode(pr)
        if not invoice.payment_hash:
            await delete_atm_payment_link(paymentid)
            return {"status": "ERROR", "reason": "Not valid payment request."}
        if not invoice.payment_hash:
            await delete_atm_payment_link(paymentid)
            return {"status": "ERROR", "reason": "Not valid payment request."}
        wallet = await get_wallet(device.wallet)
        assert wallet
        if wallet.balance_msat < (int(lnurldevicepayment.sats / 1000) + 100):
            await delete_atm_payment_link(paymentid)
            return {"status": "ERROR", "reason": "Not enough funds."}
        if lnurldevicepayment.payload != k1:
            await delete_atm_payment_link(paymentid)
            return {"status": "ERROR", "reason": "Bad K1"}
        if lnurldevicepayment.payhash != "payment_hash":
            await delete_atm_payment_link(paymentid)
            return {"status": "ERROR", "reason": "Payment already claimed"}
        try:
            lnurldevicepayment.payhash = lnurldevicepayment.payload
            lnurldevicepayment_updated = await update_lnurldevicepayment(
                lnurldevicepayment
            )
            assert lnurldevicepayment_updated
            await pay_invoice(
                wallet_id=device.wallet,
                payment_request=pr,
                max_sat=int(lnurldevicepayment_updated.sats / 1000),
                extra={"tag": "lnurldevice_withdraw"},
            )
        except Exception:
            lnurldevicepayment.payhash = "payment_hash"
            lnurldevicepayment_updated = await update_lnurldevicepayment(
                lnurldevicepayment
            )
            assert lnurldevicepayment_updated
            return {"status": "ERROR", "reason": "Failed to make payment."}
        return {"status": "OK"}
    if device.device == "switch":
        if not amount:
            return {"status": "ERROR", "reason": "No amount"}

        payment_hash, payment_request = await create_invoice(
            wallet_id=device.wallet,
            amount=int(amount / 1000),
            memo=f"{device.title} ({lnurldevicepayment.payload} ms)",
            unhashed_description=device.lnurlpay_metadata.encode(),
            extra={
                "tag": "Switch",
                "pin": str(lnurldevicepayment.pin),
                "amount": str(int(amount)),
                "comment": comment,
                "variable": variable,
                "id": paymentid,
            },
        )

        lnurldevicepayment = await update_lnurldevicepayment(lnurldevicepayment)
        resp = {
            "pr": payment_request,
            "successAction": {
                "tag": "message",
                "message": f"{int(amount / 1000)}sats sent",
            },
            "routes": [],
        }

        return resp

    payment_hash, payment_request = await create_invoice(
        wallet_id=device.wallet,
        amount=int(lnurldevicepayment.sats / 1000),
        memo=device.title,
        unhashed_description=device.lnurlpay_metadata.encode(),
        extra={"tag": "PoS"},
    )
    lnurldevicepayment.payhash = payment_hash
    lnurldevicepayment = await update_lnurldevicepayment(lnurldevicepayment)

    return {
        "pr": payment_request,
        "successAction": {
            "tag": "url",
            "description": "Check the attached link",
            "url": str(request.url_for("lnurldevice.displaypin", paymentid=paymentid)),
        },
        "routes": [],
    }
