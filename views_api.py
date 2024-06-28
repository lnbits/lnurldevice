from http import HTTPStatus

from fastapi import Depends, HTTPException, Query, Request
from loguru import logger

from lnbits.core.crud import get_user, get_wallet
from lnbits.decorators import (
    WalletTypeInfo,
    check_admin,
    get_key_type,
    require_admin_key,
)
from lnbits.utils.exchange_rates import currencies

from . import lnurldevice_ext
from .crud import (
    create_lnurldevice,
    delete_lnurldevice,
    get_lnurldevice,
    get_lnurldevices,
    update_lnurldevice,
    update_lnurldevicepayment,
)
from .models import CreateLnurldevice
from .helpers import registerAtmPayment
from lnbits.core.services import pay_invoice
from lnbits.decorators import check_user_extension_access
from lnbits.app import settings
import httpx

@lnurldevice_ext.get("/api/v1/currencies")
async def api_list_currencies_available():
    return list(currencies.keys())


@lnurldevice_ext.post("/api/v1/lnurlpos", dependencies=[Depends(require_admin_key)])
async def api_lnurldevice_create(data: CreateLnurldevice, req: Request):
    return await create_lnurldevice(data, req)


@lnurldevice_ext.put(
    "/api/v1/lnurlpos/{lnurldevice_id}", dependencies=[Depends(require_admin_key)]
)
async def api_lnurldevice_update(
    data: CreateLnurldevice, lnurldevice_id: str, req: Request
):
    return await update_lnurldevice(lnurldevice_id, data, req)


@lnurldevice_ext.get("/api/v1/lnurlpos")
async def api_lnurldevices_retrieve(
    req: Request, wallet: WalletTypeInfo = Depends(get_key_type)
):
    user = await get_user(wallet.wallet.user)
    assert user, "Lnurldevice cannot retrieve user"
    return await get_lnurldevices(user.wallet_ids, req)


@lnurldevice_ext.get(
    "/api/v1/lnurlpos/{lnurldevice_id}", dependencies=[Depends(get_key_type)]
)
async def api_lnurldevice_retrieve(req: Request, lnurldevice_id: str):
    lnurldevice = await get_lnurldevice(lnurldevice_id, req)
    if not lnurldevice:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnurldevice does not exist"
        )
    return lnurldevice


@lnurldevice_ext.delete(
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

###############
###Lightning###
###############

@lnurldevice_ext.get(
    "/api/v1/ln/{lnurldevice_id}/{p}/{ln}"
)
async def api_lnurldevice_atm_lnadress(req: Request, lnurldevice_id: str, p: str, ln: str):

    # Check device exists

    lnurldevice = await get_lnurldevice(lnurldevice_id, req)
    if not lnurldevice:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnurldevice does not exist"
        )
    
    # Register payment to avoid double pull

    lnurldevicepayment, price_msat = await registerAtmPayment(lnurldevice, p)
    if lnurldevicepayment["status"] == "ERROR":
        return lnurldevicepayment
    
    # Make payment 

    try:
        lnurldevicepayment_updated = await update_lnurldevicepayment(
            lnurldevicepayment_id=lnurldevicepayment.id, payhash=p
        )
        assert lnurldevicepayment_updated
        payment = await pay_invoice(
            wallet_id=lnurldevicepayment_updated.wallet,
            payment_request=ln,
            amount=price_msat,
            extra={"tag": "lnurldevice", "id": lnurldevicepayment.id},
        )
    except Exception as exc:
        return {"status": "ERROR", "reason": str(exc)}
    return lnurldevicepayment.id

###############
#####boltz#####
###############

@lnurldevice_ext.get(
    "'/api/v1/boltz/{lnurldevice_id}/{p}/{onchain_liquid}/{address}"
)
async def api_lnurldevice_atm_lnadress(req: Request, lnurldevice_id: str, p: str, onchain_liquid: str, address: str):

    # Check device exists

    lnurldevice = await get_lnurldevice(lnurldevice_id, req)
    if not lnurldevice:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnurldevice does not exist"
        )

    # Register payment to avoid double pull

    lnurldevicepayment, price_msat = await registerAtmPayment(lnurldevice, p)
    if lnurldevicepayment["status"] == "ERROR":
        return lnurldevicepayment

    # One less check Bolz is activated
    
    wallet = await get_wallet(lnurldevice.wallet)
    access = await check_user_extension_access(wallet.user, "boltz")
    if not access.success:
        return {"status": "ERROR", "reason": "Boltz not enabled"}
    data = {
        "wallet": lnurldevice.wallet,
        "asset": onchain_liquid,
        "amount": price_msat,
        "instant_settlement": True,
        "onchain_address": address
    }
    try:
        lnurldevicepayment_updated = await update_lnurldevicepayment(
            lnurldevicepayment_id=lnurldevicepayment.id, payhash=p
        )
        assert lnurldevicepayment_updated

        wallet = await get_wallet(lnurldevicepayment_updated.wallet)
        headers = {"X-API-KEY": wallet.adminkey}
        async with httpx.AsyncClient() as client:
            r = await client.post(
                url=f"http://{settings.host}:{settings.port}/boltz/api/v1/swap",
                headers=headers, data =data
            )
        return r.pop("wallet", None)
    except Exception as exc:
        return {"status": "ERROR", "reason": str(exc)}