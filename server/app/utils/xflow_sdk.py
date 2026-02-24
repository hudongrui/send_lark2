import os
import requests
from colorlog import getLogger
from requests import ConnectionError
from app.tools.service_helper import retry

logger = getLogger('main')

# GLOBAL VARIABLE
REQUEST_MAX_RETRY = 3


class XFlowClient:
    def __init__(self):
        self.base_url = os.environ.get('XFLOW_BASE_URL')
        self.auth_token = os.environ.get('XFLOW_AUTH_TOKEN')

        if not self.base_url or not self.auth_token:
            raise ValueError("Missing XFlow API URL or API key.")

        self.header = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {self.auth_token}'
        }

    @retry(count=REQUEST_MAX_RETRY, exceptions=ConnectionError)
    def get_process(self, process_name, trace_id=None):
        """
        Get process ID by process name.
        :param process_name:
        :param trace_id:
        :return:
        """
        is_success = False

        url = f"{self.base_url}/api/compass/process?name={process_name}"

        resp = requests.get(url, headers=self.header)
        resp.encoding = 'utf-8'
        data = resp.json()
        logger.debug(data)

        if not resp.ok:
            msg = f"Failed to get processes '{process_name}': {resp.text}"
            if trace_id:
                log_msg = msg + f" | trace_id: {trace_id}"
            logger.error(log_msg)
            return is_success, msg, None

        try:
            resp = resp.json()
            results = resp.get('results')

            if not results:
                msg = f"Failed to get process id: No process found with name '{process_name}'"
                if trace_id:
                    log_msg = msg + f" | trace_id: {trace_id}"
                logger.error(log_msg)
                return is_success, msg, None

            elif len(results) > 1:
                msg = f"Failed to get process id: Multiple process found with name '{process_name}'"
                if trace_id:
                    log_msg = msg + f" | trace_id: {trace_id}"
                logger.error(log_msg)
                return is_success, msg, None
            else:
                process_id = results[0].get('id')

        except Exception as e:
            msg = f"Failed to get process id due to unhandled exception: {e}"
            if trace_id:
                log_msg = msg + f" | trace_id: {trace_id}"
            logger.error(log_msg)
            return is_success, msg, None

        else:
            is_success = True
            # return is_success, 'OK', process_id
            return is_success, 'OK', data

    @retry(count=REQUEST_MAX_RETRY, exceptions=ConnectionError)
    def create_ticket(self, request_user, process_name, variables, trace_id=None):
        """
        Create ticket in the XFLow system.
        :param request_user:
        :param process_name: XFlow表单的唯一标识
        :param variables: 表单中需要填写的内容
        :param trace_id:
        :return:
        """
        is_success = False
        url = f"{self.base_url}/api/compass/job"

        data_raw = {
            "applicant": request_user,
            "process": process_name,
            "variables": variables,
            "viewers": {
                "users": [request_user]
            }
        }
        resp = requests.post(url, headers=self.header, json=data_raw)

        if not resp.ok:
            msg = f"Failed to create ticket: {resp.text}"
            if trace_id:
                log_msg = msg + f" | trace_id: {trace_id}"
                logger.error(log_msg)
            return is_success, msg, None

        try:
            resp_json = resp.json()
            process = resp_json.get("process")
            applicant = resp_json.get("applicant")
            ticket_id = resp_json.get("context")[0].get("job")

            logger.debug(resp_json)

        except Exception as e:
            msg = f"Failed to create ticket due to unhandled exception: {e}"
            if trace_id:
                log_msg = msg + f" | trace_id: {trace_id}"
            logger.error(log_msg)
            return is_success, msg, None

        else:
            is_success = True
            msg = f"User '{applicant}' created process '{process}' w/ ticket ID: {ticket_id}"

            if trace_id:
                msg += f" | trace_id: {trace_id}"

            logger.info(msg)

            return is_success, msg, ticket_id

    @retry(count=REQUEST_MAX_RETRY, exceptions=ConnectionError)
    def view_ticket(self, ticket_id):
        """
        API Reference: https://xflow.arcosite.bytedance.com/4fxrjdse/1k8ok8ni
        :param ticket_id:
        :return:
        """
        is_success = False
        url = f"{self.base_url}/api/compass/job/{ticket_id}"

        resp = requests.get(url, headers=self.header)
        logger.debug(resp.text)

        if not resp.ok:
            msg = f"Failed to view ticket: {ticket_id}"
            logger.error(msg)
            return is_success, msg, None

        else:
            is_success = True
            return is_success, 'OK', resp.json()

    @retry(count=REQUEST_MAX_RETRY, exceptions=ConnectionError)
    def export_process(self, process_name):
        """
        导出流程信息：https://xflow.arcosite.bytedance.com/4fxrjdse/4vreii21
        :param process_name:
        :return:
        """
        is_success = False
        url = f"{self.base_url}/api/compass/process/{process_name}/export"

        resp = requests.get(url, headers=self.header)

        if not resp.ok:
            msg = f"Failed to view ticket: {resp.text}"
            logger.error(msg)
            return is_success, msg, None
        else:
            is_success = True
            return is_success, 'OK', resp.json()
