import asyncio

from fastapi import APIRouter
from lnbits.db import Database
from loguru import logger

from .tasks import wait_for_paid_invoices

db = Database("ext_lnurldevice")

lnurldevice_ext: APIRouter = APIRouter(prefix="/lnurldevice", tags=["lnurldevice"])

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
