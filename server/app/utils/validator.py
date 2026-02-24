import json
from colorlog import getLogger
from os import environ
from pathlib import Path
logger = getLogger('main')


def load_processes():
    """
    加载XFlow Server API支持的所有process
    :return:
    """
    template_dir = Path(environ.get('PROCESS_TEMPLATE_DIR'))
    processes = {}

    try:
        for p in template_dir.glob("*.json"):
            with open(p, "r") as f:
                try:
                    data = json.load(f)
                    process_name = p.stem
                    processes[process_name] = data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to load process {p} due to JSONDecodeError: {e}")
    except Exception as e:
        logger.error(f"Failed to load processes due to unhandled exception: {e}")

    return processes


def validate_process_input(process_name, data):
    """
    检查XFlow process的输入内容是否合法，并输出符合XFlow API格式的数据
    :param data:
    :return:
    """
    is_success = False

    # 载入当前支持的工作流
    known_processes = load_processes()

    try:
        if process_name not in known_processes.keys():
            msg = f"Unknown or un-supported process: {process_name}"
            logger.error(msg)
            return is_success, msg, None

        variables = []
        for k, v in data.items():
            if k not in known_processes[process_name].keys():
                msg = f"Invalid user input. Missing required key: {k} | Process: {process_name}"
                logger.error(msg)
                return is_success, msg, None

            else:
                variables.append({
                    "name": k,
                    "value": v,
                    "label": known_processes[process_name].get(k)
                })
    except Exception as e:
        msg = f"Failed to validate process input due to unhandled exception: {e}"
        logger.error(msg)
        return is_success, msg, None

    logger.debug(variables)

    is_success = True
    return is_success, "Passed input validation", variables
