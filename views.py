from http import HTTPStatus

from fastapi import Depends, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from lnbits.core.crud import update_payment_status, get_wallet
from lnbits.core.models import User
from lnbits.core.views.api import api_payment
from lnbits.decorators import check_user_exists, check_user_extension_access

from . import lnurldevice_ext, lnurldevice_renderer
from .crud import get_lnurldevice, get_lnurldevicepayment

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
    url = urlparse(url).netloc  # Some shit to get teh id of the device
    if not url:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Unabel to parse.")
    device = await get_lnurldevice(url.id, request)
    if not device:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnurldevice not found."
        )
    wallet = get_wallet(device.wallet)
    access = await check_user_extension_access(wallet.user, "boltz")

    return lnurldevice_renderer().TemplateResponse(
        "lnurldevice/atm.html",
        {
            "request": request,
            "lnurl": lnurl,
            "device_id": url.id,
            "hash": url.hash,
            "status": access.success or None,
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
