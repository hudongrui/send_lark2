#!/usr/bin/python3
# -*- coding: utf-8 -*-
################################
# File Name   : main.py
# Author      : dongruihu
# Created On  : 2025-06-24 11:27
# Description : Lark message service
################################
import os
import logging
import uvicorn
from pathlib import Path
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from configparser import ConfigParser
from dotenv import load_dotenv
from datetime import timedelta
from app.db.base import get_db, Message
from app.tools.logger import setup_logger
from apscheduler.schedulers.background import BackgroundScheduler
from prometheus_fastapi_instrumentator import Instrumentator


# 载入配置至环境变量
def load_config():
    f = Path(__file__).parent / 'conf' / 'config.ini'
    cfg = ConfigParser()
    cfg.read(f.resolve())

    # default
    _section = "default"
    os.environ["LARK_APP_ID"] = cfg.get(_section, "APP_ID")
    os.environ["LARK_APP_SECRET"] = cfg.get(_section, "APP_SECRET")
    os.environ["LARK_STANDARD_TEMPLATE_ID"] = cfg.get(_section, "TEMPLATE_ID")
    os.environ["LOG_PATH"] = cfg.get(_section, "LOG_PATH")
    os.environ["USER_DOMAIN"] = cfg.get(_section, "USER_DOMAIN")
    os.environ["SERVICE_DOMAIN"] = cfg.get(_section, "SERVICE_DOMAIN")
    os.environ["SERVICE_PORT"] = cfg.get(_section, "SERVER_PORT")
    os.environ["DATA_KEEP_ALIVE"] = cfg.get(_section, "DATA_KEEP_ALIVE")

    _version = Path(__file__).parent / 'version.latest'
    os.environ['VERSION_INFO'] = open(f"{_version.resolve()}").read().strip()


load_config()
load_dotenv()

DEBUG_MODE = bool(os.environ.get('DEBUG_MODE') == "true")
# Event logger for application activities. Rotational
logger = setup_logger(
    log_file="%s/app.log" % os.environ.get('LOG_PATH', '/tmp/lark_msg_service/log'),
    level=logging.DEBUG if DEBUG_MODE else logging.INFO)


# Scheduled activities
def delete_old_messages():
    db = next(get_db())
    # Delete records older than 2 months
    keep_alive = int(os.environ.get('DATA_KEEP_ALIVE', 60))
    db.query(Message).filter(
        Message.created_at < db.func.now() - timedelta(days=keep_alive)
    ).delete()
    db.commit()
    db.close()
    logger.debug(f"Remove old messages that are older than {keep_alive} days.")


async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(delete_old_messages, 'interval', days=1)
    scheduler.start()
    app.state.scheduler = scheduler  # Store scheduler in app state

    yield

    app.state.scheduler.shutdown()


app = FastAPI(title="Lark Message Service", version=os.environ.get('VERSION_INFO'), lifespan=lifespan)


# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # allow_origins_function=validate_origin,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes.lark import lark_router
from app.routes.general import general_router
from app.routes.message import router as message_router


# Register blueprints
app.include_router(lark_router)
app.include_router(general_router)
app.include_router(message_router)


# For Performance metrics monitoring
instrumentator = Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/metrics"],
)
instrumentator.instrument(app).expose(app)


# Initialize semaphore and add to app state
app.state.semaphore = asyncio.Semaphore(100)  # Adjust the limit (10) as needed


if __name__ == "__main__":
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