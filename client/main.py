#!/ic/software/tools/python3/3.8.8/bin/python3
# -*- coding: utf-8 -*-
################################
# File Name   : main.py
# Author      : dongruihu
# Created On  : 2025-07-04 16:20
# Description : Webhook for IC Middle Platform
################################
import os
import logging
import uvicorn
import asyncio
from fastapi import FastAPI
from configparser import ConfigParser
from app.tools.logger import setup_logger
from app.tools.ip_filter import whitelist_middleware

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from prometheus_fastapi_instrumentator import Instrumentator


### CONFIG ###
# Event log 
def load_config():
    # Load config file
    f = f"{os.path.dirname(os.path.realpath(__file__))}/conf/config.ini"
    config = ConfigParser()
    config.read(f)

    os.environ['SERVER_HOST'] = config.get('default', 'SERVER_HOST')
    os.environ['SERVER_PORT'] = config.get('default', 'SERVER_PORT')

    os.environ['CLIENT_PORT'] = config.get('default', 'CLIENT_PORT')

    os.environ['LARK_APP_ID'] = config.get('default', 'APP_ID')
    os.environ['LARK_APP_SECRET'] = config.get('default', 'APP_SECRET')
    os.environ['DEBUG_MODE'] = config.get('default', 'DEBUG_MODE')
    os.environ['LOG_PATH'] = config.get('default', 'LOG_PATH')
    os.environ['SEMAPHORE_COUNT'] = config.get('default', 'SEMAPHORE_COUNT')

    os.environ['VERSION_INFO'] = open(f"{os.path.dirname(os.path.realpath(__file__))}/version.latest").read().strip()

    # Load blacklist
    os.environ['ALLOWED_USER'] = config.get('default', 'ALLOWED_USER')
    os.environ['ALLOWED_HOST_REGEX'] = config.get('default', 'ALLOWED_HOST_REGEX')
    # os.environ['IP_BLACKLIST'] = f"{os.path.dirname(os.path.realpath(__file__))}/conf/ip_blacklist.txt"
    # os.environ['HOSTS_FILE'] = f"{os.path.dirname(os.path.realpath(__file__))}/hosts/host.list"
    # os.environ['SECRET_FILE'] = f"{os.path.dirname(os.path.realpath(__file__))}/conf/.secret.txt"


load_config()
DEBUG_MODE = bool(os.environ.get('DEBUG_MODE') == "true")
# Event logger for application activities. Rotational
logger = setup_logger(
    log_file="%s/app.log" % os.environ.get('LOG_PATH', '/tmp/send_lark_webhook/log'),
    level=logging.DEBUG if DEBUG_MODE else logging.INFO)


app = FastAPI(title="Lark Message Service - Webhook", version=os.environ.get('VERSION_INFO'))

# Add Middleware
# app.middleware('http')(ip_ban_middleware)
# 2025/11/06: Change strategy to white-list middleware.
# NOTE: Optional - IP middleware filter.
# app.middleware('http')(whitelist_middleware)


## Define lifespan here.
# async def lifespan(app: FastAPI):
#     # 1. Initialize scheduler
#     scheduler = BackgroundScheduler()

#     cron_schedule = os.environ.get('MEEGO_SYNC_SCHEDULE')
#     sync_dir = os.environ.get('MEEGO_SYNC_DIR')
#     scheduler.add_job(
#         func=update_routine,
#         trigger=CronTrigger.from_crontab(cron_schedule),
#         args=[sync_dir]
#     )
#     logger.info(f"Initiated update_routine with schedule: {cron_schedule} | sync_dir: {sync_dir}")
#     scheduler.start()
#     app.state.scheduler = scheduler  # Store scheduler in app state

#     yield

#     # Shutdown scheduler
#     app.state.scheduler.shutdown()


from app.routes.lark import lark_router
from app.routes.general import general_router

# Register blueprints
app.include_router(general_router)
app.include_router(lark_router)

# For performance metrics monitoring
instrumentator = Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/metrics"],
)
instrumentator.instrument(app).expose(app)

app.state.semaphore = asyncio.Semaphore(int(os.environ.get('SEMAPHORE_COUNT', 100)))


if __name__ == '__main__':
    _port = os.environ.get('CLIENT_PORT')
    _log_config = f"{os.path.dirname(os.path.realpath(__file__))}/conf/logging_config.json"

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=_port,
        log_config=_log_config,
        reload=True,
        workers=1
    )
