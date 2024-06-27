from http import HTTPStatus

from fastapi import Depends, HTTPException, Query, Request
from loguru import logger

from lnbits.core.crud import get_user
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
)
from .models import CreateLnurldevice
from .helpers import registerAtmPayment

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

###Lightning###

@lnurldevice_ext.get(
    "'/api/v1/ln/{lnurldevice_id}/{p}/{ln}"]
)
async def api_lnurldevice_atm_lnadress(req: Request, lnurldevice_id: str, p: str, ln: str):
    # ln can be an invoice or lnaddress
    lnurldevice = await get_lnurldevice(lnurldevice_id, req)
    if not lnurldevice:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="lnurldevice does not exist"
        )
    lnurldevicepayment, price_msat = await registerAtmPayment(lnurldevice, p)
    if lnurldevicepayment["status"] == "ERROR":
        return lnurldevicepayment
    try:
        payment = await pay_invoice(
            wallet_id=device.wallet,
            payment_request=ln,
            amount=price_msat,
            extra={"tag": "lnurldevice", "id": lnurldevicepayment.id},
        )
    except Exception as exc:
        return {"status": "ERROR", "reason": str(exc)}
    return lnurldevicepayment.id

###Boltz###