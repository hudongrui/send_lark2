#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Test server middleware components.

For mqtt command-line test, run these two script in separate terminal:

    uv run test_middleware.py subscribe

    uv run test_middleware.py publish

"""
import pytest
import time
import sys
import random
from paho.mqtt import client as mqtt_client

#### MQTT Test ####
MQTT_SERVER = "broker.emqx.io"
MQTT_PORT = 1883
TOPIC = "send_lark/unittest"

client_id = f"publish-{random.randint(0, 1000)}"

# Preparation
def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
    # client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(MQTT_SERVER, MQTT_PORT)
    return client


def publish(client):
    msg_count = 1
    while True:
        time.sleep(1)
        msg = f"messages: {msg_count}"
        result = client.publish(TOPIC, msg)
        # result: [0, 1]
        status = result[0]
        if status == 0:
            print(f"Send `{msg}` to topic `{TOPIC}`")
        else:
            print(f"Failed to send message to topic {TOPIC}")
        msg_count += 1
        if msg_count > 5:
            break


def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")

    client.subscribe(TOPIC)
    client.on_message = on_message


def test_mqtt_publish():
    client = connect_mqtt()
    client.loop_start()
    publish(client)
    client.loop_stop()

def test_mqtt_subscribe():
    client = connect_mqtt()
    subscribe(client)
    client.loop_forever()


if sys.argv[1] == "publish":
    test_mqtt_publish()
elif sys.argv[1] == "subscribe":
    test_mqtt_subscribe()