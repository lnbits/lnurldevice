from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from lnbits.core.crud import get_standalone_payment
from lnbits.core.models import User
from lnbits.decorators import check_user_exists
from lnbits.helpers import template_renderer

from .crud import get_lnurldevice, get_lnurldevicepayment

lnurldevice_generic_router = APIRouter()


def lnurldevice_renderer():
    return template_renderer(["lnurldevice/templates"])


@lnurldevice_generic_router.get("/", response_class=HTMLResponse)
async def index(request: Request, user: User = Depends(check_user_exists)):
    return lnurldevice_renderer().TemplateResponse(
        "lnurldevice/index.html",
        {"request": request, "user": user.dict()},
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
