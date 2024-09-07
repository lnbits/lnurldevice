from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Request
from lnbits.core.crud import get_user
from lnbits.core.models import WalletTypeInfo
from lnbits.decorators import (
    require_admin_key,
    require_invoice_key,
)
from lnbits.utils.exchange_rates import currencies

from .crud import (
    create_lnurldevice,
    delete_lnurldevice,
    get_lnurldevice,
    get_lnurldevices,
    update_lnurldevice,
)
from .models import CreateLnurldevice

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
    req: Request, key_info: WalletTypeInfo = Depends(require_invoice_key)
):
    user = await get_user(key_info.wallet.user)
    assert user, "Lnurldevice cannot retrieve user"
    return await get_lnurldevices(user.wallet_ids, req)


@lnurldevice_api_router.get(
    "/api/v1/lnurlpos/{lnurldevice_id}", dependencies=[Depends(require_invoice_key)]
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
