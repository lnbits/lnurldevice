import asyncio

from fastapi import APIRouter
from loguru import logger

from .crud import db
from .tasks import wait_for_paid_invoices
from .views import lnurldevice_generic_router
from .views_api import lnurldevice_api_router
from .views_lnurl import lnurldevice_lnurl_router

lnurldevice_ext: APIRouter = APIRouter(prefix="/lnurldevice", tags=["lnurldevice"])
lnurldevice_ext.include_router(lnurldevice_generic_router)
lnurldevice_ext.include_router(lnurldevice_api_router)
lnurldevice_ext.include_router(lnurldevice_lnurl_router)

lnurldevice_static_files = [
    {
        "path": "/lnurldevice/static",
        "name": "lnurldevice_static",
    }
]
scheduled_tasks: list[asyncio.Task] = []


def lnurldevice_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def lnurldevice_start():
    from lnbits.tasks import create_permanent_unique_task

    task = create_permanent_unique_task("ext_lnurldevice", wait_for_paid_invoices)
    scheduled_tasks.append(task)


__all__ = [
    "db",
    "lnurldevice_ext",
    "lnurldevice_static_files",
    "lnurldevice_start",
    "lnurldevice_stop",
]
