#!/bin/bash

export SERVICE_HOST="127.0.0.1"
export SERVICE_PORT=8000
export CHAT_NAME="IC Middle Platform 交流群"

curl -s -X GET -H "Content-Type: application/json" \
   -H "x-app-secret: Q7ItsZ34PYqxtYu8CyxBBgN95jF5WDIh" \
   -H "x-app-id: app-15b86d8f6a83e030" \
   -H "x-username: $(whoami)" \
   --data-urlencode "name=$CHAT_NAME" \
   "http://$SERVICE_HOST:$SERVICE_PORT/lark/api/v1/get_chat_id" | jq

