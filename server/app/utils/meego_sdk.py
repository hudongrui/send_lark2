import os
import time
from typing import List
import requests
from byted_project_oapi_sdk.client import Client

from colorlog import getLogger

logger = getLogger('main')

# GLOBAL VARIABLES
QUERY_TIMEOUT = 10  # seconds
MAX_RETRY = 3


def login(func):
    def wrapper(self, *args, **kwargs):
        if not self.plugin_token or time.time() >= self.token_expired_time:
            logger.debug("Token expired, refreshing for new token.")
            self.plugin_token, self.token_expired_time = self.get_plugin_token()
        return func(self, *args, **kwargs)
    return wrapper


class MeegoClient:
    def __init__(self):
        """
        Meego API 客户端, 包含一些API接口函数, 以及封装顶层封装函数
        """
        self.base_url = os.environ.get('MEEGO_BASE_URL')
        self.plugin_id = os.environ.get('MEEGO_PLUGIN_ID')
        self.plugin_secret = os.environ.get('MEEGO_PLUGIN_SECRET')
        self.user_key = None
        if not self.base_url or not self.plugin_id or not self.plugin_secret:
            raise ValueError("Missing Meego API URL, Plugin ID, or Plugin Secret.")

        self.client = Client(
            domain=self.base_url,
            plugin_id=self.plugin_id,
            plugin_secret=self.plugin_secret,
            logger=logger
        )

        # Refresh plugin token.
        self.plugin_token, self.token_expired_time, _ = self.get_plugin_token()

        # 用于临时存储项目源数据
        self.current_project_metadata = {}
    
    def set_query_admin(self, username: str):
        """
        Set query admin.
        """
        _, _, users = self.get_users_info(usernames=[username])
        if users:
            self.user_key = users[0].get("user_key")
        else:
            raise ValueError(f"No admin or invalid configured for meego space: {username}")

    def get_plugin_token(self):
        """
        Dynamicly get plugin token.

        Reference URL: https://meego-hc.larkoffice.com/b/helpcenter/1p8d7djs/4id4bvnf

        Response body:
        {
            "data": {
                "expire_time": 7200,
                "token": "p-423383a6-7100-47ff-9d00-f36298ae0481"
            },
            "error": {
                "code": 0,
                "display_msg": {},
                "msg": "success"
            }
        }
        """
        token_url = f"{self.base_url}/open_api/authen/plugin_token"
        header = {"Content-Type": "application/json"}
        data = {
            "plugin_id": self.plugin_id,
            "plugin_secret": self.plugin_secret
        }

        resp = requests.post(token_url, headers=header, json=data)

        try:
            resp_json = resp.json()
            if resp_json.get('error', {}).get('code') == 0:
                data = resp_json.get('data', {})
                token = data.get('token')
                expire_time = data.get('expire_time', 0)
                msg = resp_json.get('error', {}).get("msg")
                return token, time.time() + expire_time, msg
            else:
                logger.error(f"Error in get_plugin_token response: {resp_json.get('error', {}).get('msg')}")
        except (ValueError, KeyError) as e:
            logger.error(f"Failed to get plugin token: {e}", exc_info=True)

        return "", 0, "Failed"

    @login
    def get_project_list(self):
        """
        获取用户有权限的空间列表
        Returns a list of project keys.

        Example response:
            {
                "err": {},
                "err_code": 0,
                "err_msg": "",
                "data": [
                    "67f621dbaf541742952701ef",
                    "67c003162de2ed84632c4125"
                ]
            }
        """
        url = f"{self.base_url}/open_api/projects"
        header = {
            "Content-Type": "application/json",
            "X-PLUGIN-TOKEN": self.plugin_token,
            "X-USER-KEY": self.user_key
        }
        body = {
            "user_key": self.user_key
        }

        resp = requests.post(url, headers=header, json=body)
        if resp.status_code == 200:
            resp_json = resp.json()
            if resp_json.get('err_code')== 0:
                data = resp_json.get('data', {})
                msg = resp_json.get('err_msg')
                return True, msg, data
            else:
                logger.error(f"Error in get_project_list response: {resp_json.get('err_msg')}")
        return False, "Failed to get_project_list", {}

    @login
    def get_project_base_info(self, project_keys: list):
        """
        获取空间基本信息

        Example response:
        "data": {
            "67f621dbaf541742952701ef": {
                "project_key": "67f621dbaf541742952701ef",
                "name": "AI芯片-Ada2",
                "simple_name": "ai_chip_ada2",
                "administrators": [
                    "7380244148231618564",
                    "7112412703645335554",
                    "7439251835023540228"
                ]
        }
        """
        url = f"{self.base_url}/open_api/projects/detail"
        header = {
            "Content-Type": "application/json",
            "X-PLUGIN-TOKEN": self.plugin_token,
            "X-USER-KEY": self.user_key
        }
        body = {
            "user_key": self.user_key,
            "project_keys": project_keys
        }

        resp =  requests.post(url, headers=header, json=body)
        if resp.status_code == 200:
            resp_json = resp.json()
            if resp_json.get('err_code') == 0:
                data = resp_json.get('data', {})
                msg = resp_json.get('err_msg')
                return True, msg, data
            else:
                logger.error(f"Error in get_project_base_info response: {resp_json.get('err_msg')}")

        return False, "Failed to get_project_base_info", {}

    @login
    def get_project_fields(self, project_key: str, work_item_type_keys: List[str]):
        """
        获取指定的工作项列表 （单空间）
        Reference URL:
            https://meego-hc.larkoffice.com/b/helpcenter/1p8d7djs/1attl6vt
        """
        # resp = self.client.field.query_project_fields(
        #     QueryProjectFieldsReqBuilder().
        #     project_key(project_key).
        #     build(),
        #     RequestOption(user_key=user_key, plugin_token=self.plugin_token)
        # )
        token_url = f"{self.base_url}/open_api/{project_key}/work_item/filter"
        header = {
            "Content-Type": "application/json",
            "X-PLUGIN-TOKEN": self.plugin_token,
            "X-USER-KEY": self.user_key
        }
        body = {
            "work_item_type_keys": work_item_type_keys
        }

        resp = requests.post(token_url, headers=header, json=body)

        if resp.status_code == 200:
            resp_json = resp.json()
            if resp_json.get('error', {}).get('code') == 0:
                data = resp_json.get('data', {})
                msg = resp_json.get('err_msg')
                return True, msg, data
            else:
                logger.error(f"Error in get_project_fields response: {resp_json.get('error', {}).get('msg')}")
        else:
            logger.error(f"Error in get_project_fields response: {resp.status_code}")
        return False, "Failed", {}

    @login
    def get_project_details(self, project_key: str, work_item_type_keys: List[str]):
        """
        获取指定的工作项列表（单空间）

        Reference URL:
            https://luccaistesting.arcosite.bytedance.com/1p8d7djs/1attl6vt
        """
        api_url = f"{self.base_url}/open_api/{project_key}/work_item/filter"
        header = {
            "Content-Type": "application/json",
            "X-PLUGIN-TOKEN": self.plugin_token,
            "X-USER-KEY": self.user_key
        }
        body = {
            "work_item_type_keys": work_item_type_keys
        }
        resp = requests.post(api_url, headers=header, json=body)
        if resp.status_code == 200:
            resp_json = resp.json()
            if resp_json.get('err_code') == 0:
                data = resp_json.get('data', {})
                msg = resp_json.get('err_msg')
                project_metadata = list(filter(lambda x: x.get('project_key') == project_key, data))
                return True, msg, project_metadata
            else:
                logger.error(f"Error in get_project_details response: {resp_json.get('err_msg')}")
        return False, "Failed to get project details", {}

    @login
    def get_project_details_across_space(self, project_key: str, work_item_type_key: str):
        """
        获取指定的工作项列表（跨空间）

        Reference URL:
            https://meego-hc.larkoffice.com/b/helpcenter/1p8d7djs/1hpwuxld

        API: {{base_url}}/open_api/work_items/filter_across_project

        Example request body:
        {
	        "work_item_type_key": "project"
        }
        """
        api_url = f"{self.base_url}/open_api/work_items/filter_across_project"
        header = {
            "Content-Type": "application/json",
            "X-PLUGIN-TOKEN": self.plugin_token,
            "X-USER-KEY": self.user_key
        }
        body = {
            "work_item_type_key": work_item_type_key  # project
        }
        resp = requests.post(api_url, headers=header, json=body)
        if resp.status_code == 200:
            resp_json = resp.json()
            if resp_json.get('err_code') == 0:
                data = resp_json.get('data', {})
                msg = resp_json.get('err_msg')
                project_metadata = list(filter(lambda x: x.get('project_key') == project_key, data))[0]
                return True, msg, project_metadata
            else:
                logger.error(f"Error in get_project_details_across_space response: {resp_json.get('err_msg')}")
        return False, msg, data

    @login
    def get_project_role_config(self, project_key: str, work_item_type_keys: List[str]):
        """
        获取流程角色配置详情
        Reference URL:
            https://meego-hc.larkoffice.com/b/helpcenter/1p8d7djs/2s90fy0i

        Example response:
        returns:
            data_dict = {
                "role_b150bb": "TPM",
                ...
            }
        """
        data_dict = {}
        for work_item_type_key in work_item_type_keys:
            api_url = f"{self.base_url}/open_api/{project_key}/flow_roles/{work_item_type_key}"
            header = {
                "Content-Type": "application/json",
                "X-PLUGIN-TOKEN": self.plugin_token,
                "X-USER-KEY": self.user_key
            }
            resp = requests.get(api_url, headers=header)
            if resp.status_code == 200:
                resp_json = resp.json()
                if resp_json.get('err_code') == 0:
                    data = resp_json.get('data', {})
                    msg = resp_json.get('err_msg')

                    for role_entry in data:
                        role_name = role_entry.get("name")
                        role_key = role_entry.get("id")
                        data_dict[role_key] = role_name
                # return True, msg, data_dict
            else:
                logger.error(f"Error in get_project_role_config response: {resp_json.get('err_msg')}")
                return False, "Failed to get_project_role_config", data_dict

        return True, msg, data_dict

    @login
    def get_users_info(self, user_keys: List[str] = [], usernames: List[str] = []):
        """
        获取用户详情

        Reference URL:
            https://meego-hc.larkoffice.com/b/helpcenter/1p8d7djs/xqbea3rp

        """
        api_url = f"{self.base_url}/open_api/user/query"
        header = {
            "Content-Type": "application/json",
            "X-PLUGIN-TOKEN": self.plugin_token
        }
        if user_keys:
            body = {
                "user_keys": user_keys
            }
        elif usernames:
            emails = list(map(lambda x: f"{x}@bytedance.com", usernames))
            body = {
                "emails": emails
            }
        else:
            return False, "Invalid user keys or usernames", {}

        resp = requests.post(api_url, headers=header, json=body)
        if resp.status_code == 200:
            resp_json = resp.json()
            if resp_json.get('err_code') == 0:
                data = resp_json.get('data', {})
                msg = resp_json.get('err_msg')

                users = []
                for item in data:
                    entry = {
                        "user_key": item.get("user_key"),
                        "name_cn": item.get("name_cn"),
                        "name_en": item.get("name_en"),
                        "email": item.get("email")
                    }
                    users.append(entry)

                return True, msg, users
            else:
                logger.error(f"Error in get_users_info response: {resp_json.get('err_msg')}")
        else:
            logger.error(f"Error in get_users_info response: {resp.status_code} | {resp.text}")

        return False, "Failed to get_users_info", {}

    @login
    def get_project_field_info(self, project_key: str, work_item_type_key: str, field_name: str):
        """
        Get project field info, and filter by field_name

        Reference URL:
            https://meego-hc.larkoffice.com/b/helpcenter/1p8d7djs/3tsposa2

        {
            "field_key": "field_69a0d0",
            "field_alias": "",
            "field_name": "项目阶段",
            "is_custom_field": true,
            "value_generate_mode": "Default",
            "field_type_key": "tree_select",
            "options": ...
        """
        api_url = f"{self.base_url}/open_api/{project_key}/field/all"
        header = {
            "Content-Type": "application/json",
            "X-PLUGIN-TOKEN": self.plugin_token,
            "X-USER-KEY": self.user_key
        }
        body = {
            "work_item_type_key": work_item_type_key
        }
        resp = requests.post(api_url, headers=header, json=body)
        if resp.status_code == 200:
            resp_json = resp.json()
            if resp_json.get('err_code') == 0:
                data = resp_json.get('data', {})
                msg = resp_json.get('err_msg')
                query_field = list(filter(lambda x: x.get("field_name") == field_name, data))
                return True, msg, query_field[0] if query_field else {}
            else:
                logger.error(f"Error in get_project_field_info response: {resp_json.get('err_msg')}")
        else:
            logger.error(f"Error in get_project_field_info response: {resp.status_code} | {resp.text}")
        return False, "Failed to get project field info", {}
    
    @login
    def get_work_item_type_keys(self, project_key: str, field_names: str):
        """
        获取空间下工作项类型
        有时 project 字段对应的工作项 project_key 并不一定是 project，需要二次查询。

        Reference URL:
            https://luccaistesting.arcosite.bytedance.com/1p8d7djs/3pjp854w
        """
        type_keys = []
        mapping_dict = {}

        api_url = f"{self.base_url}/open_api/{project_key}/work_item/all-types"
        header = {
            "Content-Type": "application/json",
            "X-PLUGIN-TOKEN": self.plugin_token,
            "X-USER-KEY": self.user_key
        }
        resp = requests.get(api_url, headers=header)
        if resp.status_code == 200:
            resp_json = resp.json()
            if resp_json.get('err_code') == 0:
                data = resp_json.get('data', {})
                msg = resp_json.get('err_msg')

                for item in data:
                    if item.get("name") in field_names:
                        type_keys.append(item.get("type_key"))
                        mapping_dict[item.get("name")] = item.get("type_key")

                return True, msg, type_keys, mapping_dict
            else:
                logger.error(f"Error in get_work_item_type_key response: {resp_json.get('err_msg')}")
        else:
            logger.error(f"Error in get_work_item_type_key response: {resp.status_code} | {resp.text}")

        return False, "Failed to get_work_item_type_key", type_keys, mapping_dict

    def set_current_project(self, project_key: str, work_item_field_names: List):
        """
        Set current project metadata. 获取项目源数据，如项目、人员分工
        """
        _, _, work_item_type_keys, work_item_type_dict = self.get_work_item_type_keys(
            project_key=project_key,
            field_names=work_item_field_names)
        logger.debug(f"Using work item type key: {work_item_type_keys}")
        _, _, project_metadata = self.get_project_details(
            project_key=project_key,
            work_item_type_keys=work_item_type_keys)
        self.current_project_metadata = project_metadata[0]  # FIXME

        return project_key, work_item_type_keys, work_item_type_dict

    def get_project_role_owners(self, role_mapping: dict = {}):
        """
        Get list of role owners.
        """
        query_field = list(filter(lambda x: x.get("field_key") == "role_owners", self.current_project_metadata.get("fields")))[0]
        role_owners = query_field.get("field_value")  # List

        if role_mapping:
            for entry in role_owners:
                role_key = entry.get("role")
                if role_key in role_mapping.keys():
                    entry["role"] = role_mapping[role_key]

        return role_owners

    def get_project_current_node(self):
        """
        获取当前项目节点
        """
        current_node = "N/A"
       
        try:
            current_nodes = self.current_project_metadata.get("current_nodes")
            current_node = current_nodes[0].get("name")
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to get current project node: {current_nodes} | {e}")
        
        return current_node
    
    def get_project_stage_field_key(self, project_key: str, work_item_type_key: str, field_name: str = "项目阶段"):
        """
        获取项目阶段字段映射键值
        """
        _, _, query_dict = self.get_project_field_info(
            project_key=project_key,
            work_item_type_key=work_item_type_key,
            field_name=field_name)

        field_key = query_dict.get("field_key")
        return field_key
    
    def get_project_stage(self, field_key: str):
        """
        获取当前项目阶段 from current_project_metadata
        """
        try:
            query_field = list(filter(lambda x: x.get("field_key") == field_key, self.current_project_metadata.get("fields")))[0]
            project_stage = query_field.get("field_value").get("label")
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to get project stage: {e}")
            project_stage = "N/A"

        return project_stage

    def get_project_block_owners(self, project_key: str, work_item_type_key: str):
        """
        获取项目Block负责人
        """
        block_info = {}
        _, _, project_metadata = self.get_project_details(
            project_key=project_key,
            work_item_type_keys=[work_item_type_key]
        )
        try:
            block_metadata = list(filter(lambda x: x.get("work_item_type_key") == work_item_type_key, project_metadata))
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to get project block owners: {e}")
            return {}

        for entry in block_metadata:
            block_name = entry.get("name")  # PCIe
            roles = list(filter(lambda x: x.get("field_key") == "role_owners", entry.get("fields")))[0]
            block_info[block_name] = roles.get("field_value")

        return block_info

    def get_state_times(self):
        """
        获取项目节点列表
        """
        try:
            state_times = self.current_project_metadata.get("state_times", [])
            return state_times
        except (ValueError, IndexError) as e:
            logger.error(f"Failed to get project stage: {e}")
            return []
    
    def get_user_mapping(self, user_keys: List[str]):
        """
        获取用户映射（支持批量查询）
        """
        BATCH_SIZE = 100  # Adjust based on API's actual user limit
        user_mapping = {}
        
        # Split user keys into batches
        for i in range(0, len(user_keys), BATCH_SIZE):
            batch_keys = user_keys[i:i+BATCH_SIZE]
            _, _, users = self.get_users_info(user_keys=batch_keys)
            
            for user in users:
                user_key = user.get("user_key")
                email = user.get("email")
                if email:
                    username = email.split("@")[0]
                    user_mapping[user_key] = username
        
        return user_mapping