import asyncio
from typing import List

from fastapi import APIRouter
from loguru import logger

from lnbits.db import Database
from lnbits.helpers import template_renderer
from lnbits.tasks import create_permanent_unique_task

db = Database("ext_lnurldevice")

lnurldevice_ext: APIRouter = APIRouter(prefix="/lnurldevice", tags=["lnurldevice"])

lnurldevice_static_files = [
    {
        "path": "/lnurldevice/static",
        "name": "lnurldevice_static",
    }
]


def lnurldevice_renderer():
    return template_renderer(["lnurldevice/templates"])


from .lnurl import *  # noqa: F401,F403
from .tasks import wait_for_paid_invoices
from .views import *  # noqa: F401,F403
from .views_api import *  # noqa: F401,F403


scheduled_tasks: list[asyncio.Task] = []


def lnurldevice_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def lnurldevice_start():
    task = create_permanent_unique_task("ext_lnurldevice", wait_for_paid_invoices)
    scheduled_tasks.append(task)
