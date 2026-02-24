#!/bin/bash

uvicorn main:app --host 0.0.0.0 --log-config conf/logging_config.json --port $PORT