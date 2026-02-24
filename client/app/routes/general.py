import os
import requests
from app.tools.service_helper import get_application_uptime
from fastapi import APIRouter

general_router = APIRouter(prefix='', tags=['general'])

@general_router.get("/", description="Default root endpoint")
async def endpoint():
    return {'message': f'Lark Message Service - Webhook | Version: {os.environ.get("VERSION_INFO")} | Maintainer: dongruihu@bytedance.com'}

@general_router.get("/hi")  # FastAPI decorator with path and tags
async def hi():  # FastAPI supports async by default
    # Test if remote service is alive.
    host = os.getenv('SERVER_HOST')
    port = os.getenv('SERVER_PORT')

    try:
        resp = requests.get(f"http://{host}:{port}/hi", timeout=3)
    except Exception as e:
        msg = f"Hi. WEBHOOK is UP but cannot connect to remote server: {e}"
    else:
        if resp.status_code == 200:
            msg = 'Hi, Webhook is UP, remote server alive.'
        else:
            msg = 'Hi. WEBHOOK is UP but cannot connect to remote server.'

    start_time, up_since = get_application_uptime()
    msg += f"\nStart time: {start_time}, Uptime: {up_since}"
    return {'message': msg}
