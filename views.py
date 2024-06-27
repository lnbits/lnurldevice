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
from .crud import get_lnurldevice, get_lnurldevicepayment, get_lnurldevicepayment_by_p
from .lnurl import xor_decrypt
from urllib.parse import urlparse, parse_qs
from loguru import logger
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
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Unable to decode lnurl.")
    logger.debug("poo")
    parsed_url = urlparse(url)
    path_segments = parsed_url.path.split('/')
    device = await get_lnurldevice((path_segments[-1]), request)
    if not device:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Unable to find device.")
    logger.debug("poo")
    query_params = parse_qs(parsed_url.query)
    p = query_params.get('p', [None])[0] 
    if p is None:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Missing 'p' parameter.")
    
    logger.debug(f"Query parameter 'p': {p}")
    if len(p) % 4 > 0:  # Adjust for base64 padding if necessary
        p += "=" * (4 - (len(p) % 4))

    data = base64.urlsafe_b64decode(p)
    try:
        decrypted = xor_decrypt(device.key.encode(), data)
        logger.debug(decrypted)
    except Exception as exc:
        logger.debug(str(exc))
        return {"status": "ERROR", "reason": str(exc)}
    
    wallet = await get_wallet(device.wallet)
    if not wallet:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Wallet not found.")
    
    lnurldevicepayment = await get_lnurldevicepayment_by_p(p)
    if lnurldevicepayment:
        if lnurldevicepayment.payload == lnurldevicepayment.payhash:
            return {"status": "ERROR", "reason": "Payment already claimed"}

    access = await check_user_extension_access(wallet.user, "boltz")

    return lnurldevice_renderer().TemplateResponse(
        "lnurldevice/atm.html",
        {
            "request": request,
            "lnurl": lnurl,
            "device_id": device.id,
            "boltz": access.success or None,
            "p": p,
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
