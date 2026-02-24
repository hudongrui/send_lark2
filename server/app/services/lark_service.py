import os, requests, functools, time, re
import lark_oapi as lark
import json
import asyncio
from typing import Dict, List, Tuple
from colorlog import getLogger
import logging
from lark_oapi.api.drive.v1 import *
from lark_oapi.api.im.v1 import *
from lark_oapi.api.contact.v3 import *

logger = getLogger("main")
logger.setLevel(logging.DEBUG)


class ServiceException(Exception):
    def __init__(self, message, error_code=500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

    def __str__(self):
        return f"{self.message} (Error Code: {self.error_code})"

# Decorator class
def tenant_access(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            if not self.tenant_access_token:
                self.get_tenant_access_token()
            elif self.tenant_token_expire_at < time.time():
                self.get_tenant_access_token()
            
            return func(self, *args, **kwargs)
        except Exception as e:
            logger.error(f"[fail to get tenant_access] Error: {e}", exc_info=True)
            return func(self, *args, **kwargs)

    return wrapper


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        # Use domain as the key for instances
        domain = kwargs.get('domain', os.environ.get('SERVICE_DOMAIN', "open.feishu.cn"))
        key = (cls, domain)

        if key not in cls._instances:
            # Create a new instance if one does not exist for this domain
            instance = super(Singleton, cls).__call__(*args, **kwargs)
            # Store in dict
            cls._instances[key] = instance

        return cls._instances[key]


class LarkAPIModule(metaclass=Singleton):
    def __init__(self, domain=None):
        if domain == "bytedance":
            self.lark_app_id = os.environ.get('BD_LARK_APP_ID')
            self.lark_app_secret = os.environ.get('BD_LARK_APP_SECRET')
            self.lark_service_domain = os.environ.get('BD_SERVICE_DOMAIN', "open.larkoffice.com")
            self.DEFAULT_USER_DOMAIN = os.environ.get('BD_USER_DOMAIN', 'bytedance.com')
            self.STANDARD_TEMPLATE_ID = os.environ.get('BD_LARK_STANDARD_TEMPLATE_ID')
        else:
            self.lark_app_id = os.environ.get('LARK_APP_ID')
            self.lark_app_secret = os.environ.get('LARK_APP_SECRET')
            self.lark_service_domain = os.environ.get('SERVICE_DOMAIN', "open.feishu.cn")
            self.DEFAULT_USER_DOMAIN = os.environ.get('USER_DOMAIN', 'picoheart.com')
            self.STANDARD_TEMPLATE_ID = os.environ.get('LARK_STANDARD_TEMPLATE_ID')

        if self.lark_app_id is None or self.lark_app_secret is None:
            raise ServiceException("LARK_APP_ID or LARK_APP_SECRET is NOT setup.")

        self.client = lark.Client.builder() \
            .app_id(f'{self.lark_app_id}') \
            .app_secret(f'{self.lark_app_secret}') \
            .log_level(lark.LogLevel.DEBUG) \
            .build()

        self.tenant_access_token = None
        self.tenant_token_expire_at = time.time()
        # TODO: All clients need to handle code: 429 -> Too many requests.
        # Refence link: https://open.larkoffice.com/document/server-docs/api-call-guide/frequency-control

    def get_tenant_access_token(self):
        url = f"https://{self.lark_service_domain}/open-apis/auth/v3/tenant_access_token/internal/"
        headers = {
            "Content-Type": "application/json; charset=utf-8"
        }
        body = {
            "app_id": f'{self.lark_app_id}',
            "app_secret": f'{self.lark_app_secret}'
        }
        response = requests.post(url, json=body, headers=headers, timeout=5)
        if response.status_code == 200:
            _token = response.json().get("tenant_access_token")
            _expire = int(response.json().get("expire"))
            self.tenant_access_token = _token
            self.tenant_token_expire_at = time.time() + _expire - 60  # 60s buffer
            return _token
        else:
            raise Exception("Failed to get tenant_access_token: {}".format(response.text))

    @tenant_access
    def search_chat_id_from_feed(self, id: str) -> Tuple[int, str, str]:
        """
        Search chat ID by feed id. - INTERNAL

        Reference URL:
            https://open.larkoffice.com/document/server-docs/group/chat/chat-id-description-bytedance
        """
        url = f"https://{self.lark_service_domain}/open-apis/exchange/v3/cid2ocid"
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self.tenant_access_token}"
        }
        body = {
            "chat_id": id
        }
        resp = requests.post(url, json=body, headers=headers)
        if not resp.ok:
            logger.error(
                f"client.convert_chat_id failed, code: {resp.status_code}, msg: {resp.text}")
            return resp.status_code, "", resp.text

        resp_json = resp.json()
    
        _code = resp_json["code"]
        
        if _code == 0:
            open_chat_id = resp_json["open_chat_id"]
            
            if any(_id is None for _id in open_chat_id):
                logger.error(f"open_chat_id is None: {open_chat_id}")
                return 10003, "", "Invalid open_chat_id"

            logger.debug(f"Converted chat_id: {id} to open_chat_id: {open_chat_id}")
            return 0, open_chat_id, resp_json["msg"]
        elif _code == 10003:
            logger.error(f"code: {_code} | msg: {resp_json['msg']}")
            logger.debug(f"url: {url} | body: {body} | header: {headers}")
            return _code, "", resp_json["msg"]

        else:
            return _code, "", resp_json["msg"]


    @tenant_access
    def search_chat_id(self, chat_name: str) -> Tuple[int, str, str]:
        """
        Search chat ID by chat name. - INTERNAL

        Reference URL:
            https://open.larkoffice.com/document/server-docs/group/chat/search?appId=cli_a6cfca9fe87bd013
        """
        request: SearchChatRequest = SearchChatRequest.builder() \
            .query(chat_name) \
            .build()
        
        resp: SearchChatResponse = self.client.im.v1.chat.search(request)

        if not resp.success():
            logger.error(
                f"client.contact.v1.chat.search failed, code: {resp.code}, msg: {resp.msg}, log_id: {resp.get_log_id()}")
            return int(resp.code), None, resp.msg

        result = json.loads(lark.JSON.marshal(resp.data.items))

        return resp.code, result, resp.msg


    def get_batch_user_id(self, emails: List) -> Tuple[int, List, str]:
        """
        通过邮箱获取用户ID

        Reference URL: 
            https://open.larkoffice.com/document/server-docs/contact-v3/user/batch_get_id?appId=cli_a61ce64fb5f8d013

        """
        request: BatchGetIdUserRequest = BatchGetIdUserRequest.builder() \
            .user_id_type("open_id") \
            .request_body(BatchGetIdUserRequestBody.builder() \
                .emails(emails) \
                .build()) \
            .build()

        resp: BatchGetIdUserResponse = self.client.contact.v3.user.batch_get_id(request)

        if not resp.success():
            logger.error(
                f"client.contact.v3.user.batch_get_id failed, code: {resp.code}, msg: {resp.msg}, log_id: {resp.get_log_id()}")
            return int(resp.code), [], resp.msg

        result = json.loads(lark.JSON.marshal(resp.data.user_list))

        return resp.code, result, resp.msg


    def send_message(self, receive_id: str, content: str = None, title: str = "芯片事件平台通知", title_color: str = "green", receive_id_type: str = 'email', msg_type: str = 'text', template_id: str = None, template_variables: Dict = None) -> Tuple[int, str, str]:
        """
        使用标准消息模版 发送消息

        Standard Card ID: AAqzQaSO1T5jw

        卡片搭建工具：https://open.feishu.cn/cardkit/editor?cardId=AAqzQaSO1T5jw

        From single tenant -> 50 QPS / 1000 QPM

        To single user: 5 QPS
        Reference URL: https://open.larkoffice.com/document/server-docs/im-v1/message/create?appId=cli_a61ce64fb5f8d013
        """
        if msg_type == 'standard':  # For standard template message
            template_id = self.STANDARD_TEMPLATE_ID
            content = self.temp(content)
            template_variables = {
                "title": title,
                "title_color": title_color,
                "message": content
            }
            logger.debug(f'using template id: {template_id} | message: {content}')

            msgContent = {
                "type": "template",
                "data": {
                    "template_id": template_id,
                    "template_variable": template_variables
                }
            }
            _content = self.preprocess_content(msgContent)  # Convert {user: $username} to <at>
            msg_type = 'interactive'


        # Text is NOT used.
        elif msg_type == 'text':
            msgContent = {
                "text": content,
            }
            _content = self.preprocess_msg_content(msgContent, msg_type)
            _content = _content.replace('\\\\n', '\\n')


        # Ordinary Text Message
        elif msg_type == 'post' and title:
            msg_content = self.preprocess_post_content(content)
            msgContent = {
                "zh_cn": {
                    "title": title,
                    "content": msg_content
                }
            }
            _content = self.preprocess_msg_content(msgContent, msg_type)
        elif msg_type == 'interactive':  # For card_template
            msgContent = {
                "type": "template",
                "data": {
                    "template_id": template_id,
                    "template_variable": template_variables
                }
            }
            # _content = self.preprocess_msg_content(msgContent, msg_type)
            _content = self.preprocess_content(msgContent)
            # logger.warning(json.dumps(msgContent))
        else:
            return 40001, "", "Unsupported message type"

        request: CreateMessageRequest = CreateMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(CreateMessageRequestBody.builder()
                .receive_id(receive_id)
                .msg_type(msg_type)
                .content(_content)
                .build()) \
            .build()

        # TODO: Confirm client handle request? Threading OK?
        resp: CreateMessageResponse = self.client.im.v1.message.create(request)

        if not resp.success():
            logger.error(
                f"client.im.v1.message.create failed, code: {resp.code}, msg: {resp.msg}, log_id: {resp.get_log_id()}")

            return resp.code, "", resp.msg

        result = lark.JSON.marshal(resp.data.message_id)

        return resp.code, result, resp.msg

    @tenant_access
    def batch_send_message(self, open_ids: List, msg_type: str = 'text', title: str = "芯片事件平台通知", title_color: str = "green", content: str = "", template_id: str = None, template_variables: Dict = None) -> Tuple[int, str, str]:
        """
        Send message to multiple users.

        Reference URL: https://open.larkoffice.com/document/server-docs/im-v1/batch_message/send-messages-in-batches

        NOTE: 异步接口，有延迟。若单用户或群聊发消息，或业务要求发消息不能有延迟，请使用send_message接口

        For card:
        {
        "open_ids": [
            "ou_a18fe85d22e7633852d8104226e99eac",
            "ou_9204a37300b3700d61effaa439f34295"
        ],
        "department_ids": [
            "od-5b91c9affb665451a16b90b4be367efa"
        ],
        "msg_type": "interactive",
        "card": {
            "type": "template",
            "data": {
            "template_id": "ctp_xxxxxx",
            "template_variable": {
                "var_xxx": "xxxxxx"
            }
            }
        }
        }
        """
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        # Use 'msg_type' to decide payload type
        msg_type = 'interactive'

        logger.debug(f"[batch_send_message] open_ids: {open_ids} | msg_type: {msg_type} | title: {title} | title_color: {title_color} | content: {content} | template_id: {template_id} | template_variables: {template_variables}")
        if not template_id:
            template_id = self.STANDARD_TEMPLATE_ID
            content = self.temp(content)
            template_variables = {
                "title": title,
                "title_color": title_color,
                "message": content
            }
        else:
            logger.debug(f'[batch_send_message.preprocess_content] using template variables: {template_variables}')
            template_variables = self.preprocess_content(template_variables, to_json=True)

        logger.debug(f'using template id: {template_id} | template_variables: {template_variables}')

        msgContent = {
            "type": "template",
            "data": {
                "template_id": template_id,
                "template_variable": template_variables
            }
        }
        # _content = self.preprocess_content(msgContent)  # Convert {user: $username} to <at>

        body = {
            "open_ids": open_ids,
            "msg_type": msg_type,
            "card": msgContent
        }

        # print(json.dumps(body, ensure_ascii=False, indent=2))

        url = f"https://{self.lark_service_domain}/open-apis/message/v4/batch_send/"
        resp = requests.post(url, headers=headers, json=body, timeout=20)

        if not resp.ok:
            logger.error(
                f"client.batch_send failed, code: {resp.status_code}, msg: {resp.text}")
            return resp.status_code, "", resp.text

        resp_json = resp.json()
    
        _code = resp_json["code"]
        
        if _code == 0:
            return 0, resp_json["data"]["message_id"], resp_json["msg"]

        else:
            return _code, "", resp_json["msg"]

    @tenant_access
    def convert_chat_id(self, chat_id: str, id_type: str = 'chat_id') -> str:
        """
        Convert <Lark chat ID> to <Lark open ID>

        Reference URL: https://open.larkoffice.com/document/server-docs/group/chat/chat-id-description-bytedance

        """
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        body = {
            id_type: chat_id
        }

        url = f"https://{self.lark_service_domain}/open-apis/exchange/v3/cid2ocid/"
        resp = requests.post(url, headers=headers, json=body, timeout=5)

        if not resp.ok:
            logger.error(
                f"convert_chat_id failed, code: {resp.status_code}, msg: {resp.text}")
            return resp.status_code, "", resp.text

        resp_json = resp.json()
        _code = resp_json["code"]

        if id_type == 'chat_id':
            result_id_type = 'open_chat_id'
        else:
            result_id_type = 'chat_id'
        
        if _code == 0:
            _msg = resp_json['msg']
            _id = resp_json[result_id_type]
            logger.debug(f"[convert_chat_id] '{id_type}' to '{result_id_type}': {_id}")
            return 0, _id, _msg

        else:
            _msg = resp_json['msg']
            logger.error(f"[convert_chat_id] Failed to convert '{id_type}'({chat_id}) to '{result_id_type}': {_msg}")
            return _code, None, _msg

    def process_recipients(self, recipients: List[str]) -> Tuple[List[str], str]:
        """
        Process recipients to get open_ids and chat_id.

        If all recipients are open_ids, return them as is.
        If any recipient is a chat_id, convert it to open_id and return all open_ids.

        :param recipients: List of recipients (open_ids or chat_ids)
        :return: Tuple of open_ids and chat_id (if any)
        """
        receive_ids = []  # NOTE: Default email names.
        chat_id = None

        chat_id_regex = r'^group_chat: (.*)'
        open_id_regex = r'^(oc_[a-zA-Z0-9]{32})$'

        old_id_regex = r'^[a-zA-Z0-9]{19}$'  # Keep for historical reason

        for r in recipients:
            if re.search(chat_id_regex, r): # convert chat_name -> chat_id
                chat_name = re.search(chat_id_regex, r).groups()[0]
                _, chat_id, _ = self.search_chat_id(chat_name)
            elif re.search(open_id_regex, r):  # oc_* -> chat_id
                chat_id = re.search(open_id_regex, r).groups()[0]
            elif re.search(old_id_regex, r):  # old_id -> open_id
                raise ServiceException(f"Feed ID ({r}) is no longer supported.")
            else:
                _domain = self.DEFAULT_USER_DOMAIN
                _email = f"{r}@{_domain}"
                receive_ids.append(_email)

        return receive_ids, chat_id

    def preprocess_post_content(self, msg_content: str) -> list:
        """
        批量处理 '{user: $username}'格式的用户名
        """
        # For batch send message reconstruct
        at_user_regex = r'{user: (.*?)}'
        user_mapping = {}
        if re.findall(at_user_regex, msg_content):
            usernames = re.findall(at_user_regex, msg_content)
            _domain = self.DEFAULT_USER_DOMAIN
            emails = list(map(lambda x: f"{x}@{_domain}", usernames))
            _code, user_dict, _msg = self.get_batch_user_id(emails)
            if _code != 0:
                raise ServiceException(f"Failed to get batch user id for {emails}. {_msg}", error_code=_code)

            for _dict in user_dict:
                user_mapping[_dict.get('email').replace(f'@{_domain}', '')] = _dict['user_id']

            # _splits = re.split(r'{user: (.*?)}|\n|\\n', msg_content)
            # _splits = re.split(r'{user: (.*?)}', msg_content)
            # try:
            #     # _splits.remove('')  # Remove empty strings
            #     _splits = list(filter(lambda x: x != '' and x != None, _splits))
            # except ValueError:
            #     pass

        result = []
        for line in re.split(r'\n|\\n', msg_content):
            _clause = []

            # Convert user
            _splits = re.split(r'{user: (.*?)}', line)
            try:
                # _splits.remove('')  # Remove empty strings
                _splits = list(filter(lambda x: x != '' and x != None, _splits))
            except ValueError:
                pass
            for o in _splits:  # ['Test message ', 'dongruihu', 'user2', ' Yeah.']
                if o in user_mapping.keys():
                    _clause.append({
                        "tag": "at",
                        "user_id": user_mapping.get(o)
                    })
                else:
                    _clause.append({
                        "tag": "text",
                        "text": o
                    })
            if _clause:
                result.append(_clause)
        return result

    def preprocess_content(self, msg_content: str, to_json: bool = False) -> str:
        """对提及用户进行转译"""
        at_user_regex = r'{user: (.*?)}'

        result = json.dumps(msg_content)
        if re.findall(at_user_regex, result):
            user_mapping = {}
            usernames = re.findall(at_user_regex, result)
            _domain = self.DEFAULT_USER_DOMAIN
            # emails = list(map(lambda x: f"{x}@{_domain}", usernames))
            for u in usernames:
                user_mapping[u] = f"{u}@{_domain}"

            for _match in re.findall(at_user_regex, result):
                # logger.warning(r'{user: %s}' % _match)
                result = re.sub(r'{user: %s}' % _match, '<at email=\\\"%s\\\"></at>' % user_mapping.get(_match), result)
            
        if to_json:
            result = json.loads(result)

        return result

    def preprocess_msg_content(self, msg_content: Dict, msg_type: str) -> str:
        """
        Supports @user in plain/rich text, or card_template
        """
        at_user_regex = r'{user: (.*?)}'

        result = json.dumps(msg_content)
        if re.findall(at_user_regex, result):
            usernames = re.findall(at_user_regex, result)
            _domain = self.DEFAULT_USER_DOMAIN
            emails = list(map(lambda x: f"{x}@{_domain}", usernames))
            _code, user_dict, _msg = self.get_batch_user_id(emails)
            if _code != 0:
                raise ServiceException(f"Failed to get batch user id for {emails}. {_msg}", error_code=_code)
            
            user_mapping = {}
            for _dict in user_dict:
                user_mapping[_dict.get('email').replace(f'@{_domain}', '')] = _dict['user_id']

            # logger.warning(f"User mapping: {user_mapping}")
            # Lookup user-id
            # if msg_type == 'standard':
            #     for _match in re.findall(at_user_regex, result):
            #         # logger.warning(r'{user: %s}' % _match)
            #         result = re.sub(r'{user: %s}' % _match, '<at user_id=%s></at>' % user_mapping.get(_match), result)
            if msg_type != 'interactive':
                for _match in re.findall(at_user_regex, result):
                    # logger.warning(r'{user: %s}' % _match)
                    result = re.sub(r'{user: %s}' % _match, '<at user_id=\\\"%s\\\"></at>' % user_mapping.get(_match), result)
                    # result = re.sub(r'\n|\\n', f'\\\\n', result)

            else:
                for _match in re.findall(at_user_regex, result):
                    # logger.warning(r'{user: %s}' % _match)
                    result = re.sub(r'{user: %s}' % _match, user_mapping.get(_match), result)

            return result
        else:
            return result

    def temp(self, msg_content: str) -> str:
        t = msg_content.replace('\\n', '\n')
        t = t.replace(']', '\]')
        t = t.replace('[', '\[')
        return t

    async def sleep(self):
        await asyncio.sleep(1)
        return 0