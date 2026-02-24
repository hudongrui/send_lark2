#!/ic/software/tools/python3/3.8.8/bin/python3
# -*- coding: utf-8 -*-
################################
# File Name   : client
# Author      : dongruihu
# Created On  : 2025-07-24 10:53:36
# Description :
################################
import os
import re
import sys
import yaml
import uuid
import json
import requests
import urllib.parse
from json import JSONDecodeError
from getpass import getuser
from typing import Tuple, List


# GLOBAL VARIABLES
DEFAULT_QUERY_TIMEOUT = 10
DEFAULT_PAYLOAD_SIZE = 2048
OVERFLOW_RETURN_CODE = 2

DEBUG = "bold bright_black"
WARNING = "bold yellow"
ERROR = "bold red"


class MessageClient:
    def __init__(self, console=None, debug: bool = False, domain: str = None, secret: str = None):
        self.timeout = int(os.environ.get('LARK_QUERY_TIMEOUT', DEFAULT_QUERY_TIMEOUT))
        host = os.getenv('LARK_CLIENT_HOST')
        port = os.getenv('LARK_CLIENT_PORT')

        self.console = console
        self.base_url = f"http://{host}:{port}"
        self.debug = debug

        self.user_mapping_cfg = None

        self.default_header = {
            "x-app-id": os.getenv('LARK_APP_ID'),
            "x-app-secret": os.getenv('LARK_APP_SECRET'),
            "x-username": getuser(),
            "Content-type": "application/json"
        }

        if secret:
            self.default_header.update({
                "x-secret": secret
            })

        self.domain = domain

    def set_user_mapping(self, map_cfg: str):
        self.user_mapping_cfg = map_cfg

    def print(self, msg: str, level=ERROR):
        if self.console:
            self.console.print(msg, style=level)
        else:
            print(msg)

    def __str__(self) -> str:
        return self.base_url

    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def generate_trace_id() -> str:
        """Generate W3C-compliant trace ID"""
        return uuid.uuid4().hex[:16]

    def check_health(self):
        """
        Check for program health.
        :return:
        """
        url = f"{self.base_url}/hi"
        try:
            resp = requests.get(url=url, timeout=5)
        except Exception as e:
            # self.console.print(f"Lark message service: internal error | Exception: {e}", style=ERROR)
            self.print(f"Lark message service: internal error | Exception: {e}")
        else:
            if resp.status_code != 200:
                # self.console.print(f"Lark message service: internal error. Response code: {resp.status_code}", style=ERROR)
                self.print(f"Lark message service: internal error. Response code: {resp.status_code}")
            else:
                _msg = resp.json().get('message')
                # self.console.print(_msg, style=DEBUG)
                self.print(_msg)

    def enable_debug(self):
        self.debug = True

    def get_chat_id(self, group_chat: str) -> str:
        """
        Search chat ID by group chat name.
        """
        _group_chat = urllib.parse.quote(group_chat)
        url = f"{self.base_url}/lark/api/v1/get_chat_id?name={_group_chat}"
        if self.domain:
            url += f"&domain={self.domain}"

        resp = requests.get(url=url, headers=self.default_header, timeout=self.timeout)
        return self.process_response(resp, quiet=True)

    def get_chat_id_from_feed(self, chat_number: str) -> str:
        """
        Search chat ID by group chat name.
        """
        _group_chat = urllib.parse.quote(chat_number)
        url = f"{self.base_url}/lark/api/v1/get_chat_id_from_feed?id={_group_chat}"
        if self.domain:
            url += f"&domain={self.domain}"

        resp = requests.get(url=url, headers=self.default_header, timeout=self.timeout)
        return self.process_response(resp, quiet=True)

    def send_lark_msg(self, content: str, recipients: list, title: str, header_color: str = 'green') -> Tuple[bool, int, str]:
        trace_id = self.generate_trace_id()
        data = {
            "title": title,
            "content": content,
            "recipients": recipients,
            "header_color": header_color,
            "trace_id": trace_id
        }

        url = f"{self.base_url}/lark/api/v1/send_lark_msg"
        if self.domain:
            url += f"?domain={self.domain}"

        if self.debug:
            # self.console.print(f"Send message to recipients: {recipients}", style=DEBUG)
            self.print(f"Send message to recipients: {recipients}")
        if self.debug:
            # self.console.print(f'URL: {url} | timeout: {self.timeout}s', style=DEBUG)
            # self.console.print(f'content: {content}', style=DEBUG)
            self.print(f'URL: {url} | timeout: {self.timeout}s')
            self.print(f'content: {content}')
        resp = requests.post(url=url, headers=self.default_header, json=data, timeout=self.timeout)

        return self.process_response(resp)

    def send_card_msg(self, card_id: str, content: str, recipients: list) -> Tuple[bool, int, str]:
        # Check if content matching json format:
        if content == "":
            content = "{}"
        else:
            try:
                content = json.dumps(json.loads(content))
            except JSONDecodeError:
                # self.console.print(f"Invalid JSON content: {content}", style=ERROR)
                self.print(f"Invalid JSON content: {content}")
                sys.exit(-1)

        trace_id = self.generate_trace_id()

        data = {
            "card_id": card_id,
            "content": content,
            "recipients": recipients,
            "trace_id": trace_id
        }

        url = f"{self.base_url}/lark/api/v1/send_card"
        if self.domain:
            url += f"?domain={self.domain}"

        if self.debug:
            # self.console.print(f"Send card message to recipients: {recipients}, using card ID: {card_id}", style=DEBUG)
            self.print(f"Send card message to recipients: {recipients}, using card ID: {card_id}")

        if self.debug:
            # self.console.print(f'URL: {url} | timeout: {self.timeout}s', style=DEBUG)
            # self.console.print(f'content: {content}', style=DEBUG)
            self.print(f'URL: {url} | timeout: {self.timeout}s')
            self.print(f'content: {content}')
        resp = requests.post(url=url, headers=self.default_header, json=data, timeout=self.timeout)

        return self.process_response(resp, trace_id)

    def process_response(self, resp: requests.Response, trace_id: str = None, quiet: bool = False) -> Tuple[int, str, str]:
        """
        Handle response body.

        {
            "return_code": 0,
            "message": "success",
            "trace_id": "1234567890"
        }
        """
        if resp.status_code != 200:
            msg = f"Failed to process request: {resp.text}"
            # self.console.print(f"{msg} | Response: {resp.status_code}", style=DEBUG)
            self.print(f"{msg} | Response: {resp.status_code}")

            return resp.status_code, msg, trace_id
        else:  # 处理请求体
            try:
                resp_json = resp.json()

                code = resp_json.get("return_code")
                msg = resp_json.get("message")
                trace_id = resp_json.get("trace_id")

                if code == 0:
                    if self.debug:
                        # self.console.print(f"Message sent successfully! Trace ID: {trace_id}", style=DEBUG)
                        self.print(f"Message sent successfully! Trace ID: {trace_id} | msg: {msg}\n")
                    return code, msg, trace_id
                else:
                    # self.console.print(f"{code} | Failed to send message: {msg} | Trace ID: {trace_id}", style=ERROR)
                    self.print(f"{code} | Failed to send message: {msg} | Trace ID: {trace_id}")
                    return code, msg, trace_id

            except Exception as e:
                # self.console.print(f"Invalid response format: {str(e)}", style=ERROR)
                self.print(f"Invalid response format: {str(e)}")

                return 500, "Internal server error", trace_id

    def get_translated_recipients(self, group_chat: str, recipients: List[str]) -> List:
        """
        使用特殊的账号人员映射
        """
        user_list = []
        with open(self.user_mapping_cfg) as f:
            cfg = yaml.safe_load(f)

        _match = False
        for r in recipients:
            if r in cfg['mapping'].keys():
                user_list.extend(cfg['mapping'][r])
                _match = True
                continue

            for _pattern in cfg['fuzzy_mapping'].keys():
                if re.match(_pattern, r):
                    user_list.extend(cfg['fuzzy_mapping'][_pattern])
                    _match = True
                    break

            if not _match:
                user_list.append(r)

        if group_chat:
            user_list.append(f"group_chat: {group_chat}")

        # Remove duplate usernames if any.
        user_list = list(set(user_list))

        return user_list

    def preprocess_content(self, content: str, title: str, is_text: bool = False) -> str:
        """
        Preprocess message content and replace \n
        """
        if os.path.exists(content) and not (os.path.isdir(content)):
            with open(os.path.realpath(content), 'r') as f:
                content = f.read()

        else:
            content = content.replace('\n', '\\n')

        payload_size = int(os.environ.get('PAYLOAD_SIZE', DEFAULT_PAYLOAD_SIZE))
        # Card Message.
        if len(content) > payload_size and not is_text:
            # self.console.print(f"[ERROR] Message size exceeds limit: {DEFAULT_PAYLOAD_SIZE}", style=ERROR)
            self.print(f"[ERROR] Message size exceeds limit: {payload_size}")
            sys.exit(OVERFLOW_RETURN_CODE)
        # Text Message
        elif len(content) > payload_size and is_text:
            # self.console.print(f"[ERROR] Message size exceeds limit: {DEFAULT_PAYLOAD_SIZE}", style=ERROR)
            self.print(f"[WARNING] Message size exceeds limit: {payload_size}, cut off message string.\n")
            content = f'{content[:payload_size-3]}...'
        # Title
        elif len(title) > payload_size:
            # self.console.print(f"[ERROR] Message size exceeds limit: {DEFAULT_PAYLOAD_SIZE}", style=ERROR)
            self.print(f"[ERROR] Message size exceeds limit: {payload_size}")
            sys.exit(OVERFLOW_RETURN_CODE)

        return content, title
