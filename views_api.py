from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from lnbits.core.crud import get_user, get_wallet
from lnbits.core.models import WalletTypeInfo
from lnbits.decorators import (
    get_key_type,
    require_admin_key,
)
from lnbits.utils.exchange_rates import currencies

from .crud import (
    create_lnurldevice,
    delete_lnurldevice,
    get_lnurldevice,
    get_lnurldevices,
    update_lnurldevice,
    update_lnurldevicepayment,
    get_lnurldevicepayments,
    get_lnurldevicepayment,
    delete_atm_payment_link,
)
from lnbits.core.views.api import api_lnurlscan
from .models import CreateLnurldevice, Lnurlencode
from .helpers import register_atm_payment
from lnbits.core.services import pay_invoice
from lnbits.decorators import check_user_extension_access
from lnbits.app import settings
from bolt11 import decode as bolt11_decode
from lnbits.lnurl import encode as lnurl_encode
import httpx

lnurldevice_api_router = APIRouter()

@lnurldevice_api_router.get("/api/v1/currencies")
async def api_list_currencies_available():
    return list(currencies.keys())


@lnurldevice_api_router.post(
    "/api/v1/lnurlpos", dependencies=[Depends(require_admin_key)]
)
async def api_lnurldevice_create(data: CreateLnurldevice, req: Request):
    return await create_lnurldevice(data, req)


@lnurldevice_api_router.put(
    "/api/v1/lnurlpos/{lnurldevice_id}", dependencies=[Depends(require_admin_key)]
)
async def api_lnurldevice_update(
    data: CreateLnurldevice, lnurldevice_id: str, req: Request
):
    return await update_lnurldevice(lnurldevice_id, data, req)


@lnurldevice_api_router.get("/api/v1/lnurlpos")
async def api_lnurldevices_retrieve(
    req: Request, wallet: WalletTypeInfo = Depends(get_key_type)
):
    user = await get_user(wallet.wallet.user)
    assert user, "Lnurldevice cannot retrieve user"
    return await get_lnurldevices(user.wallet_ids, req)


@lnurldevice_api_router.get(
    "/api/v1/lnurlpos/{lnurldevice_id}", dependencies=[Depends(get_key_type)]
)
async def api_lnurldevice_retrieve(req: Request, lnurldevice_id: str):
    lnurldevice = await get_lnurldevice(lnurldevice_id, req)
    if not lnurldevice:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnurldevice does not exist"
        )
    return lnurldevice


@lnurldevice_api_router.delete(
    "/api/v1/lnurlpos/{lnurldevice_id}", dependencies=[Depends(require_admin_key)]
)
async def api_lnurldevice_delete(req: Request, lnurldevice_id: str):
    lnurldevice = await get_lnurldevice(lnurldevice_id, req)
    if not lnurldevice:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Lnurldevice does not exist."
        )

    await delete_lnurldevice(lnurldevice_id)


#########ATM API#########


@lnurldevice_api_router.get("/api/v1/atm")
async def api_atm_payments_retrieve(
    req: Request, wallet: WalletTypeInfo = Depends(get_key_type)
):
    user = await get_user(wallet.wallet.user)
    assert user, "Lnurldevice cannot retrieve user"
    lnurldevices = await get_lnurldevices(user.wallet_ids, req)
    deviceids = []
    for lnurldevice in lnurldevices:
        if lnurldevice.device == "atm":
            deviceids.append(lnurldevice.id)
    return await get_lnurldevicepayments(deviceids)

@lnurldevice_api_router.post("/api/v1/lnurlencode",  dependencies=[Depends(get_key_type)])
async def api_lnurlencode(
    data: Lnurlencode
):
    lnurl = lnurl_encode(data.url)
    logger.debug(lnurl)
    if not lnurl:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Lnurl could not be encoded."
        )
    return lnurl

@lnurldevice_api_router.delete(
    "/api/v1/atm/{atm_id}", dependencies=[Depends(require_admin_key)]
)
async def api_atm_payment_delete(req: Request, atm_id: str):
    lnurldevice = await get_lnurldevicepayment(atm_id)
    if not lnurldevice:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="ATM payment does not exist."
        )

    await delete_atm_payment_link(atm_id)


###############
###Lightning###
###############


@lnurldevice_api_router.get("/api/v1/ln/{lnurldevice_id}/{p}/{ln}")
async def get_lnurldevice_payment_lightning(
    req: Request, lnurldevice_id: str, p: str, ln: str
):
    """
    Handle Lightning payments for atms via invoice, lnaddress, lnurlp.
    """
    ln = ln.strip().lower()

    lnurldevice = await get_lnurldevice(lnurldevice_id, req)
    if not lnurldevice:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnurldevice does not exist"
        )

    wallet = await get_wallet(lnurldevice.wallet)
    if not wallet:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Wallet does not exist connected to atm, payment could not be made",
        )
    lnurldevicepayment, price_msat = await register_atm_payment(lnurldevice, p)
    if not lnurldevicepayment:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Payment already claimed."
        )
    
    # If its an invoice check its a legit invoice
    if ln[:4] == "lnbc":
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Invoices not supported."
        )

    # If its an lnaddress or lnurlp get the request from callback
    elif ln[:5] == "lnurl" or "@" in ln and "." in ln.split("@")[-1]:
        data = await api_lnurlscan(ln)
        if data.get("status") == "ERROR":
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail=data.get("reason")
            )
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url= f"{data['callback']}?amount={lnurldevicepayment.sats * 1000}"
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail="Could not get callback from lnurl",
                )
            ln = response.json()['pr']

    # If ln is gibberish, return an error
    else:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Wrong format for payment, could not be made. Use invoice, LNaddress or LNURLp",
        )

    # Finally log the payment and make the payment
    try:
        lnurldevicepayment, price_msat = await register_atm_payment(lnurldevice, p)
        lnurldevicepayment_updated = await update_lnurldevicepayment(
            lnurldevicepayment_id=lnurldevicepayment.id, payhash=lnurldevicepayment.payload
        )
        assert lnurldevicepayment_updated
        if ln[:4] == "lnbc":
            payment = await pay_invoice(
                wallet_id=lnurldevice.wallet,
                payment_request=ln,
                max_sat=price_msat / 1000,
                extra={"tag": "lnurldevice", "id": lnurldevicepayment.id},
            )
        assert payment
    except Exception as exc:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(exc))

    return lnurldevicepayment.id


###############
#####boltz#####
###############


@lnurldevice_api_router.get("'/api/v1/boltz/{lnurldevice_id}/{p}/{onchain_liquid}/{address}")
async def get_lnurldevice_payment_boltz(
    req: Request, lnurldevice_id: str, p: str, onchain_liquid: str, address: str
):
    """
    Handle Boltz payments for atms.
    """
    lnurldevice = await get_lnurldevice(lnurldevice_id, req)
    if not lnurldevice:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnurldevice does not exist"
        )

    lnurldevicepayment, price_msat = await register_atm_payment(lnurldevice, p)
    if lnurldevicepayment.get("status") == "ERROR":
        return lnurldevicepayment

    wallet = await get_wallet(lnurldevice.wallet)
    access = await check_user_extension_access(wallet.user, "boltz")
    if not access.success:
        return {"status": "ERROR", "reason": "Boltz not enabled"}

    data = {
        "wallet": lnurldevice.wallet,
        "asset": onchain_liquid.replace("-", "/"),
        "amount": price_msat,
        "instant_settlement": True,
        "onchain_address": address,
    }
    try:
        lnurldevicepayment_updated = await update_lnurldevicepayment(
            lnurldevicepayment.id, p
        )
        assert lnurldevicepayment_updated
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=f"http://{settings.host}:{settings.port}/boltz/api/v1/swap",
                headers={"X-API-KEY": wallet.adminkey},
                data=data,
            )
        return response.json()
    except Exception as exc:
        return {"status": "ERROR", "reason": str(exc)}
