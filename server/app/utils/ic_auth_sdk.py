import os
import requests
import logging
from typing import Dict, Tuple
from colorlog import getLogger
from requests import ConnectionError, ReadTimeout
from app.tools.service_helper import retry

# GLOBAL VARIABLE
REQUEST_MAX_RETRY = 3

class IcAuthClient:
    def __init__(self) -> None:
        _service = os.environ.get("IC_AUTH_URL")
        _port = os.environ.get("IC_AUTH_PORT")
        
        self.url = f"{_service}:{_port}"
        self.auth_token =  os.environ.get("IC_AUTH_TOKEN")  # API_TOKEN

        if not _service or not self.auth_token:
            raise ValueError("Missing ic-auth API url or API key")

        self.header = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.auth_token}'
        }

    @retry(count=REQUEST_MAX_RETRY, exceptions=(ConnectionError, ReadTimeout))
    def create_ticket(self, creator: str, data: Dict) -> Tuple[bool, str, str]:
        """
        创建流程工单
        """
        url = f"{self.url}/requestfiletransfer"

        data = {
            "creator": creator,
            "data": data
        }

        resp = requests.post(url, headers=self.header, json=data, verify=False)  # 跳过SSL证书验证，解决自签名证书问题

        if not resp.ok:
            msg = f"Failed to create ticket: {resp.text}"
            return False, msg, None

        try:
            resp_json = resp.json()
            logging.debug(resp_json)

            _success = resp_json.get('status', 'failed') == 'success'
            _message = resp_json.get('message')
            ticket_id = resp_json.get('data')

            if _success:
                logging.info(f"User '{creator}' created process w/ ticket ID: {ticket_id}")
            else:
                logging.info(f"User '{creator}' failed to created process: {_message}")

            return _success, _message, ticket_id
        except Exception as e:
            logging.error(f"[ic_auth_sdk] Failed to create ticket due to unhandled exception: {e}", exc_info=True)
            return False, f"[ic_auth_sdk] Failed to create ticket due to unhandled exception: {e}", None
