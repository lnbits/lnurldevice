import base64
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from lnbits.core.crud import (
    get_installed_extensions,
    get_standalone_payment,
    get_wallet,
)
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer
from lnbits.utils.exchange_rates import fiat_amount_as_satoshis
from lnurl import decode as lnurl_decode
from lnurl import encode as lnurl_encode
from loguru import logger

from .crud import get_lnurldevice, get_lnurldevicepayment, get_recent_lnurldevicepayment
from .helpers import xor_decrypt

lnurldevice_generic_router = APIRouter()


def lnurldevice_renderer():
    return template_renderer(["lnurldevice/templates"])


@lnurldevice_generic_router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return lnurldevice_renderer().TemplateResponse(
        "lnurldevice/index.html",
        {"request": request, "user": user.dict()},
    )


@lnurldevice_generic_router.get("/atm", response_class=HTMLResponse)
async def atmpage(request: Request, lightning: str):
    # Debug log for the incoming lightning request
    logger.debug(lightning)

    # Decode the lightning URL
    url = str(lnurl_decode(lightning))
    if not url:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Unable to decode lnurl."
        )

    # Parse the URL to extract device ID and query parameters
    parsed_url = urlparse(url)
    device_id = parsed_url.path.split("/")[-1]
    device = await get_lnurldevice(device_id, request)
    if not device:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Unable to find device."
        )

    # Extract and validate the 'p' parameter
    p = parse_qs(parsed_url.query).get("p", [None])[0]
    if p is None:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Missing 'p' parameter."
        )
    # Adjust for base64 padding if necessary
    p += "=" * (-len(p) % 4)

    # Decode and decrypt the 'p' parameter
    try:
        data = base64.urlsafe_b64decode(p)
        decrypted = xor_decrypt(device.key.encode(), data)
    except Exception as exc:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=f"{exc!s}"
        ) from exc

    # Determine the price in msat
    if device.currency != "sat":
        price_msat = await fiat_amount_as_satoshis(decrypted[1] / 100, device.currency)
    else:
        price_msat = decrypted[1]

    # Check wallet and user access
    wallet = await get_wallet(device.wallet)
    if not wallet:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Wallet not found."
        )

    # check if boltz payouts is enabled but also check the boltz extension is enabled
    access = False
    if device.extra == "boltz":
        installed_extensions = await get_installed_extensions(active=True)
        for extension in installed_extensions:
            if extension.id == "boltz" and extension.active:
                access = True
                logger.debug(access)

    # Attempt to get recent payment information
    recent_pay_attempt = await get_recent_lnurldevicepayment(p)

    # Render the response template
    return lnurldevice_renderer().TemplateResponse(
        "lnurldevice/atm.html",
        {
            "request": request,
            "lnurl": lightning,
            "amount": int(((int(price_msat) / 100) * device.profit) + int(price_msat)),
            "device_id": device.id,
            "boltz": True if access else False,
            "p": p,
            "recentpay": recent_pay_attempt.id if recent_pay_attempt else False,
            "used": (
                True
                if recent_pay_attempt
                and recent_pay_attempt.payload == recent_pay_attempt.payhash
                else False
            ),
        },
    )


@lnurldevice_generic_router.get(
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
    payment = await get_standalone_payment(lnurldevicepayment.payhash)
    if not payment:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Payment not found."
        )
    status = await payment.check_status()
    if status.success:
        return lnurldevice_renderer().TemplateResponse(
            "lnurldevice/paid.html", {"request": request, "pin": lnurldevicepayment.pin}
        )
    return lnurldevice_renderer().TemplateResponse(
        "lnurldevice/error.html",
        {"request": request, "pin": "filler", "not_paid": True},
    )


@lnurldevice_generic_router.get("/print/{payment_id}", response_class=HTMLResponse)
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

    lnurl = lnurl_encode(
        str(
            request.url_for(
                "lnurldevice.lnurl_v1_params", device_id=lnurldevicepayment.deviceid
            )
        )
        + "?atm=1&p="
        + lnurldevicepayment.payload
    )
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
