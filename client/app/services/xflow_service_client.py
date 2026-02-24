import os
import time
import json
import requests
import hashlib
from colorlog import getLogger

logger = getLogger("main")


class ServiceException(Exception):
    def __init__(self, message, error_code=500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def __str__(self):
        return f"{self.message} (Error Code: {self.error_code})"


class XflowServiceClient:
    """
    Client service interacting between XFLOW (@sysops) and User request (@IC dev)
    """

    def __init__(self):
        _host = os.environ.get("SERVER_HOST")
        _port = os.environ.get("SERVER_PORT")

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

    def view_ticket(self):
        headers = {
            "app-id": self.app_id,
            "app-secret": self.app_secret,
            "Content-Type": "application/json"
        }

        request_url = f"{self.service_url}/xflow/api/v1/view_ticket"
        resp = requests.get(url=request_url, headers=headers)
        # resp = requests.get(url=request_url)
        print(resp.text)

        return False, "Not implemented yet", resp.text

    def create_ticket(self, request_user, process_name, variables: dict):
        # template | value dict
        headers = {
            "x-app-id": self.app_id,
            "x-app-secret": self.app_secret,
            "Content-Type": "application/json"
        }

        # Generate request token, for trace ID.
        current_timestamp = time.strftime('%Y%m%d%H%M%S')
        trace_id = hashlib.md5(f'{process_name}_{current_timestamp}'.encode('utf-8')).hexdigest()
        logger.info(f'Generated request trace_id: {trace_id}')

        data = {
            "request_user": request_user,
            "process_name": process_name,
            "variables": variables,
            "trace_id": trace_id
        }

        request_url = f"{self.service_url}/xflow/api/v1/create_ticket"
        resp = requests.post(url=request_url, headers=headers, json=data)

        resp_json = resp.json()
        if "is_success" not in resp_json:
            msg = f"Failed to create ticket: {resp_json} | error code: {resp.status_code} | trace_id: {trace_id}"
            logger.error(msg)
            raise ServiceException(msg)

        is_success = resp_json['is_success']
        msg = resp_json['message']
        ticket_id = resp_json['ticket_id']

        return is_success, msg, ticket_id, trace_id
