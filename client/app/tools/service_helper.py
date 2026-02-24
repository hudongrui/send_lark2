import psutil
import os
import time
import uuid
from functools import wraps
from fastapi.responses import JSONResponse
from fastapi import Request

api_key = {
    'api-key': {
        "app-id": "app-15b86d8f6a83e030",
        "app-secret": "Q7ItsZ34PYqxtYu8CyxBBgN95jF5WDIh",
        "status": "active"
    },
    'api-key-test': {
        "app-id": "app-test",
        "app-secret": "app-secret",
        "status": "active"
    },
    'tmp-key': {
        "app-id": "app-id-test",
        "app-secret": "app-secret-test",
        "status": "active"
    }
}

def generate_trace_id() -> str:
    """Generate W3C-compliant trace ID"""
    return uuid.uuid4().hex[:16]


def is_api_key_valid(app_id, app_secret):
    """
    检查 API Key 是否有效
    """
    for api_key_name, api_key_info in api_key.items():
        if (api_key_info['app-id'] == app_id
                and api_key_info['app-secret'] == app_secret
                and api_key_info['status'] == 'active'):
            return True
    return False


def api_auth_required(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):  # Make wrapper async
        # Get API Key from headers
        api_key = request.headers.get('x-app-id')
        api_secret = request.headers.get('x-app-secret')

        # Check auth presence
        if not api_key or not api_secret:
            return JSONResponse(content={'error': '[webhook] auth info is required'}, status_code=401)

        # Validate credentials
        if is_api_key_valid(api_key, api_secret):
            return await func(request, *args, **kwargs)  # Await the async route function
        return JSONResponse(content={'error': 'Invalid API Key'}, status_code=401)

    return wrapper


def get_application_uptime():
    """
    Returns application start time & uptime.
    """
    p = psutil.Process(os.getpid())
    t = p.create_time()
    start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t))

    uptime = time.time() - t

    # pretty print uptime
    d = {
        'yrs': uptime // (365 * 24 * 3600),
        'months': uptime // (30 * 24 * 3600),
        'days': uptime // (24 * 3600),
        'hrs': uptime // 3600,
        'min': uptime // 60
    }

    up_since = 'just now'
    for k, v in d.items():
        if v > 0:
            up_since = f'{v} {k}'
            break

    return start_time, up_since
