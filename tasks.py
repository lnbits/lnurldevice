import asyncio

from lnbits.core.models import Payment
from lnbits.core.services import websocketUpdater
from lnbits.helpers import get_current_extension_name
from lnbits.tasks import register_invoice_listener

from .crud import get_lnurldevicepayment, update_lnurldevicepayment
from loguru import logger

async def wait_for_paid_invoices():
    invoice_queue = asyncio.Queue()
    register_invoice_listener(invoice_queue, get_current_extension_name())

    while True:
        payment = await invoice_queue.get()
        await on_invoice_paid(payment)


async def on_invoice_paid(payment: Payment) -> None:
    # (avoid loops)
    if payment.extra.get("tag") == "Switch":
        lnurldevicepayment = await get_lnurldevicepayment(payment.extra["id"])

        if not lnurldevicepayment:
            return
        if lnurldevicepayment.payhash == "used":
            return

        lnurldevicepayment = await update_lnurldevicepayment(
            lnurldevicepayment_id=payment.extra["id"], payhash="used"
        )
        comment = payment.extra["comment"]
        payload = lnurldevicepayment.payload
        if payload:
            payload = int(payload) * int(lnurldevicepayment.sats)

        if comment:
            return await websocketUpdater(
                lnurldevicepayment.deviceid,
                f"{lnurldevicepayment.pin}-{payload}-{comment}",
            )
        return await websocketUpdater(
            lnurldevicepayment.deviceid,
            f"{lnurldevicepayment.pin}-{lnurldevicepayment.payload}",
        )
