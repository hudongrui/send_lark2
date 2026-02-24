import os
from app.tools.service_helper import get_application_uptime
# from app.core.mqtt import mqtt
from fastapi import APIRouter

general_router = APIRouter(prefix='', tags=['general'])

@general_router.get("/", description="Default root endpoint")
async def endpoint():
    return {'message': f'Lark Message Service | Version: {os.environ.get("VERSION_INFO")} | Maintainer: dongruihu@bytedance.com'}, 200

@general_router.get("/hi")  # FastAPI decorator with path and tags
async def hi():  # FastAPI supports async by default
    # Test if remote service is alive.
    msg = 'Hi, Server alive'

    start_time, up_since = get_application_uptime()
    msg += f"\nStart time: {start_time}, Uptime: {up_since}"
    return {'message': msg}, 200


# @general_router.get("/test_mq")
# async def test_mq():
#     import json
#     obj = {
#         "title": "Test title",
#         "content": "Test webhook message",
#         "recipients": ["dongruihu"],
#         "header_color": "green"
#     }
#     try:
#         mqtt.publish("lark/messages", json.dumps(obj))
#     except:
#         return {"result": False, "message": "Internal server error, failed to publish message to MQTT"}, 500

#     return {"result": True, "message": "Test message sent successfully"}, 200
