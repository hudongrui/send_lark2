#!/ic/software/tools/python3/3.8.8/bin/python3
# -*- coding: utf-8 -*-
################################
# File Name   : message_service_client.py
# Author      : dongruihu
# Created On  : 2025-07-04 16:20
# Description : Text & card message forwarding client.
################################
import os
import time
import requests
import hashlib
import asyncio
from typing import Dict, Tuple
from colorlog import getLogger

logger = getLogger("main")


class ServiceException(Exception):
    def __init__(self, message, error_code=500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def __str__(self):
        return f"{self.message} (Error Code: {self.error_code})"


class MessageServiceClient:
    """
    Client service interacting between Server (@BD) and User request (@IC dev)
    """

    def __init__(self) -> None:
        _host = os.environ.get('SERVER_HOST')
        _port = os.environ.get('SERVER_PORT')
        

        app_id = os.environ.get('LARK_APP_ID')
        app_secret = os.environ.get('LARK_APP_SECRET')

        service_url = f"http://{_host}:{_port}"

        if app_id is None or app_secret is None:
            raise ServiceException("APP_ID or APP_SECRET is NOT setup.")

        if _host is None or _port is None:
            raise ServiceException("SERVER HOST or PORT is NOT setup.")

        self.app_id = app_id
        self.app_secret = app_secret
        self.service_url = service_url

        self.default_headers = {
            "x-app-id": os.getenv('LARK_APP_ID'),
            "x-app-secret": os.getenv('LARK_APP_SECRET'),
            "Content-type": "application/json"
        }

        self.timeout = int(os.environ.get("REQUEST_TIMEOUT", 30))

    async def get_chat_id_from_feed(self, request_body: Dict, domain: str = None) -> Tuple[int, str, str]:
        """
        Get chat id by name.

        return_code
        msg
        data
        """
        url = f"{self.service_url}/lark/api/v1/get_chat_id_from_feed"
        if domain:
            url += f"?domain={domain}"

        logger.info(f'url:{url} | request_body:{request_body}')

        resp = requests.get(url=url, headers=self.default_headers, json=request_body, timeout=self.timeout)

        if resp.status_code != 200:
            msg = f"Failed to process request: {resp.text}"
            logger.error(f"{msg} | Response: {resp.status_code}")
            return resp.status_code, msg, []
        else:  # 处理请求体
            try:
                resp_json = resp.json()

                code = resp_json.get("return_code")
                message = resp_json.get("message")
                chat_ids = resp_json.get("data")

                if code == 0:
                    return code, message, chat_ids
                else:
                    logger.error(f"{code} | Failed to get chat id: {message}")
                    return code, message, []

            except Exception as e:
                logger.error(f"Invalid response format: {str(e)}", exc_info=True)
                return 500, "Internal server error", []


    async def get_chat_id(self, request_body: Dict, domain: str = None) -> Tuple[int, str, str]:
        """
        Get chat id by name.

        return_code
        msg
        data
        """
        url = f"{self.service_url}/lark/api/v1/get_chat_id"
        if domain:
            url += f"?domain={domain}"
        logger.info(f'url:{url} | request_body:{request_body}')

        resp = requests.get(url=url, headers=self.default_headers, json=request_body, timeout=self.timeout)

        if resp.status_code != 200:
            msg = f"Failed to process request: {resp.text}"
            logger.error(f"{msg} | Response: {resp.status_code}")
            return resp.status_code, msg, []
        else:  # 处理请求体
            try:
                resp_json = resp.json()

                code = resp_json.get("return_code")
                message = resp_json.get("message")
                chat_ids = resp_json.get("data")

                if code == 0:
                    return code, message, chat_ids
                else:
                    logger.error(f"{code} | Failed to get chat id: {message}")
                    return code, message, []

            except Exception as e:
                logger.error(f"Invalid response format: {str(e)}", exc_info=True)
                return 500, "Internal server error", []


    async def send_message(self, request_body: Dict, domain: str = None) -> Tuple[int, str, str]:
        """
        Send single message.
        """
        trace_id = request_body.get("trace_id")
        url = f"{self.service_url}/lark/api/v1/send_lark_msg"
        if domain:
            url += f"?domain={domain}"
        resp = requests.post(url=url, headers=self.default_headers, json=request_body, timeout=self.timeout)

        return self.process_response(resp, trace_id)

    async def send_card(self, request_body: Dict, domain: str = None) -> Tuple[int, str, str]:
        """
        Send card based on card_id & variables
        """
        trace_id = request_body.get("trace_id")
        url = f"{self.service_url}/lark/api/v1/send_card"
        if domain:
            url += f"?domain={domain}"
        resp = requests.post(url=url, headers=self.default_headers, json=request_body, timeout=self.timeout)

        return self.process_response(resp, trace_id)


    def process_response(self, resp: requests.Response, trace_id: str) -> Tuple[int, str, str]:
        if resp.status_code != 200:
            msg = f"Failed to process request: {resp.text}"
            logger.error(f"{msg} | Response: {resp.status_code}")
            return resp.status_code, msg, trace_id
        else:  # 处理请求体
            try:
                resp_json = resp.json()

                code = resp_json.get("return_code")
                msg = resp_json.get("message")
                trace_id = resp_json.get("trace_id")

                if code == 0:
                    logger.debug(f"Message sent successfully! Trace ID: {trace_id}")
                    return code, msg, trace_id
                else:
                    logger.error(f"{code} | Failed to send message: {msg} | Trace ID: {trace_id}")
                    return code, msg, trace_id

            except Exception as e:
                logger.error(f"Invalid response format: {str(e)}", exc_info=True)
                return 500, "Internal server error", trace_id


    async def sleep(self):
        await asyncio.sleep(1)
        return None


CLIENT = MessageServiceClient()

async def get_msg_client() -> MessageServiceClient:
    return CLIENT