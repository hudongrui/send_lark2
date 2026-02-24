
import os
import requests
from pathlib import Path
from configparser import ConfigParser
from colorlog import getLogger

logger = getLogger("main")


def update_routine(base_dir: str):
    """
    向ic_middle_platform服务端发送请求并同步项目数据结构至本地路径
    """
    logger.info(f"Start to sync project layout under directory: {base_dir}")

    _host = os.environ.get("SERVER_HOST")
    _port = os.environ.get("SERVER_PORT")

    service_url = f"http://{_host}:{_port}"

    headers = {
        "app-id": os.environ.get('LARK_APP_ID'),
        "app-secret": os.environ.get('LARK_APP_SECRET'),
        "Content-Type": "application/json"
    }

    request_url = f"{service_url}/meego/api/v1/get_project_layout"
    resp = requests.get(url=request_url, headers=headers)
    if resp.status_code != 200:
        logger.error(f"Failed to sync project layout, status code: {resp.status_code}")
    else:
        resp_json = resp.json()
        is_success = resp_json['is_success']
        msg = resp_json['message']
        data = resp_json['data']

        if not is_success:
            logger.error(f"Failed to sync project layout, message: {msg}")
        else:
            logger.debug(f"Successfully sync project layout, message: {msg}")

        for project_name, content in data.items():
            with open(f"{base_dir}/spec.{project_name}.yaml", "w") as f:
                f.write(content)

        logger.info(f"Sync complete. Available project info: {list(data.keys())}")


def sync_project_config():
    scheduler = BlockingScheduler()
    cron_schedule, sync_dir = get_sync_config()

    scheduler.add_job(
        func=update_routine,
        trigger=CronTrigger.from_crontab(cron_schedule),
        args=[sync_dir])
    
    scheduler.start()