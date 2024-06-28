from http import HTTPStatus
import base64
from fastapi import Depends, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from lnbits.core.crud import update_payment_status, get_wallet
from lnbits.core.models import User
from lnbits.core.views.api import api_payment
from lnbits.decorators import check_user_exists, check_user_extension_access
from lnbits.lnurl import decode as lnurl_decode

from . import lnurldevice_ext, lnurldevice_renderer
from .crud import get_lnurldevice, get_lnurldevicepayment, get_lnurldevicepayment_by_p, get_recent_lnurldevicepayment
from .lnurl import xor_decrypt
from urllib.parse import urlparse, parse_qs
from loguru import logger
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis
from .helpers import checkAtmPaymentExists
import json
from lnbits.lnurl import encode as lnurl_encode

templates = Jinja2Templates(directory="templates")


@lnurldevice_ext.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return lnurldevice_renderer().TemplateResponse(
        "lnurldevice/index.html",
        {"request": request, "user": user.dict()},
    )


@lnurldevice_ext.get("/atm/{lnurl}", response_class=HTMLResponse)
async def index(request: Request, lnurl: str):
    url = str(lnurl_decode(lnurl))
    if not url:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Unable to decode lnurl."
        )

    parsed_url = urlparse(url)
    path_segments = parsed_url.path.split("/")
    device = await get_lnurldevice((path_segments[-1]), request)
    if not device:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Unable to find device."
        )

    query_params = parse_qs(parsed_url.query)
    p = query_params.get("p", [None])[0]
    if p is None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Missing 'p' parameter."
        )

    if len(p) % 4 > 0:  # Adjust for base64 padding if necessary
        p += "=" * (4 - (len(p) % 4))

    data = base64.urlsafe_b64decode(p)
    try:
        decrypted = xor_decrypt(device.key.encode(), data)
        logger.debug(decrypted)
    except Exception as exc:
        return {"status": "ERROR", "reason": str(exc)}

    wallet = await get_wallet(device.wallet)
    if not wallet:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Wallet not found."
        )

    lnurldevicepayment = await get_lnurldevicepayment_by_p(p)
    if lnurldevicepayment:
        if lnurldevicepayment.payload == lnurldevicepayment.payhash:
            return {"status": "ERROR", "reason": "Payment already claimed"}

    access = await check_user_extension_access(wallet.user, "boltz")

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
    try:
        recentPayAttempt = await get_recent_lnurldevicepayment(p)
    except Exception as exc:
        recentPayAttempt = False
    return lnurldevice_renderer().TemplateResponse(
        "lnurldevice/atm.html",
        {
            "request": request,
            "lnurl": lnurl,
            "amount": int(price_msat / 1000),
            "device_id": device.id,
            "boltz": access.success or None,
            "p": p,
            "recentpay": recentPayAttempt.id,
        },
    )


@lnurldevice_ext.get(
    "/{paymentid}", name="lnurldevice.displaypin", response_class=HTMLResponse
)
async def displaypin(request: Request, paymentid: str):
    lnurldevicepayment = await get_lnurldevicepayment(paymentid)
    if not lnurldevicepayment:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="No lnurldevice payment"
        )
    device = await get_lnurldevice(lnurldevicepayment.deviceid, request)
    if not device:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnurldevice not found."
        )
    status = await api_payment(lnurldevicepayment.payhash)
    if status["paid"]:
        await update_payment_status(
            checking_id=lnurldevicepayment.payhash, pending=True
        )
        return lnurldevice_renderer().TemplateResponse(
            "lnurldevice/paid.html", {"request": request, "pin": lnurldevicepayment.pin}
        )
    return lnurldevice_renderer().TemplateResponse(
        "lnurldevice/error.html",
        {"request": request, "pin": "filler", "not_paid": True},
    )


@lnurldevice_ext.get("/print/{payment_id}", response_class=HTMLResponse)
async def print_receipt(request: Request, payment_id):
    lnurldevicepayment = await get_lnurldevicepayment(payment_id)
    if not lnurldevicepayment:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Payment link does not exist."
        )
    device = await get_lnurldevice(lnurldevicepayment.deviceid, request)
    if not device:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Unable to find device."
        )
    
    lnurl = lnurl_encode(str(request.url_for(
        "lnurldevice.lnurl_v1_params", device_id=lnurldevicepayment.deviceid
    )) + "?atm=1&p=" + lnurldevicepayment.payload)
    logger.debug(lnurl)
    return lnurldevice_renderer().TemplateResponse(
        "lnurldevice/atm_receipt.html",
        {
            "request": request,
            "id": lnurldevicepayment.id,
            "deviceid": lnurldevicepayment.deviceid,
            "devicename": device.title,
            "payhash": lnurldevicepayment.payhash,
            "payload": lnurldevicepayment.payload,
            "sats": lnurldevicepayment.sats,
            "timestamp": lnurldevicepayment.timestamp,
            "lnurl": lnurl,
        },
    )