import os
import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_mqtt import FastMQTT, MQTTConfig
from logging import getLogger

logger = getLogger("main")

# NOTE: SSL/TLS transport not used, for detailed usage: https://sabuhish.github.io/fastapi-mqtt/getting-started/
mqtt_config = MQTTConfig(
    broker=os.environ.get('BROKER', 'localhost'),
    port=int(os.environ.get('PORT', 1883)),
    reconnect_retries=3
)
mqtt = FastMQTT(config=mqtt_config)


# Shutdown MQTT client
# async def handle_shutdown(signum, frame):
#     logger.info("Received shutdown signal, disconnecting MQTT client..")
#     await mqtt.client.disconnect()
#     logger.info("MQTT client disconnected.")
#     sys.exit(0)


# # Register signal handlers
# signal.signal(signal.SIGINT, handle_shutdown)
# signal.signal(signal.SIGTERM, handle_shutdown)


# @asynccontextmanager
# async def _lifespan(_app: FastAPI):
#     # await mqtt.mqtt_startup()
#     yield
#     # await mqtt.mqtt_shutdown()


@mqtt.on_connect()
def connect(client, flags, rc, properties):
    mqtt.client.subscribe("lark/messages")
    logger.info(f"Connected to MQTT broker: {client}")

# @mqtt.on_message()
# async def message(client, topic, payload, qos, properties):
#     """
#     Receive ANY messages (from any topic)
#     """
#     logger.info(f"[topic: {topic}] Received message: {payload.decode()}")
#     return 0

@mqtt.subscribe("lark/messages")
async def message_to_topic(client, topic, payload, qos, properties):
    """Receive mesage from specific topic: lark/messages"""
    logger.info(f"[topic: {topic}] Received message: {payload.decode()}")


# @mqtt.on_disconnect()
# async def disconnet(client, packet, exc=None):
#     await mqtt.client.disconnect()
#     logger.info(f"Disconnected from MQTT broker: {client}")


# @mqtt.on_subscribe()
# def subscribe(client, mid, qos, properties):
#     logger.info(f"Subscribed to {client} {mid}")


# from fastapi import FastAPI
# import paho.mqtt.client as mqtt  # Replace with your actual MQTT library

# # Initialize MQTT client (copy your existing configuration here)
# client = mqtt.Client()

# Add any necessary callbacks or configuration
# client.on_connect = lambda client, userdata, flags, rc: print(f"Connected with result code {rc}")


async def mqtt_consumer():
    """MQTT consumer that processes Lark requests"""
    def on_request(client, userdata, msg):
        loop = asyncio.get_event_loop()
        loop.create_task(process_lark_request(msg))

    mqtt_client.subscribe("lark/requests")
    mqtt_client.message_callback_add("lark/requests", on_request)

async def process_lark_request(msg):
    """Process Lark request and publish response"""
    from app.services.lark_service import LarkAPIModule
    import json

    request = json.loads(msg.payload)
    client = LarkAPIModule()

    try:
        receive_ids, chat_id = client.process_recipients(request['recipients'])
        response = {
            'request_id': request['request_id'],
            'receive_ids': receive_ids,
            'chat_id': chat_id,
            'status': 'success'
        }
    except Exception as e:
        response = {
            'request_id': request['request_id'],
            'error': str(e),
            'status': 'error'
        }

    await mqtt_client.publish(f"lark/responses/{request['request_id']}", json.dumps(response))
