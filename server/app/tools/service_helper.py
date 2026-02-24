import psutil
import os
import time
import logging
from functools import wraps
from inspect import iscoroutinefunction
from fastapi.responses import JSONResponse
from fastapi import Request


api_key = {
    'api-key': {  # For encrypted message between server & webhook client.
        "app-id": "$LARK_APP_ID",  # NOTE: replace to ACTUAL lark info
        "app-secret": "$LARK_APP_SECRET",
        "status": "active"
    },
    'api-key-test': {
        "app-id": "app-id-test",
        "app-secret": "app-secret-test",
        "status": "active"
    }
}


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

        if not api_key or not api_secret:  # Temp FIX for historical reason.
            api_key = request.headers.get('app-id')
            api_secret = request.headers.get('app-secret')

        # Check auth presence
        if not api_key or not api_secret:
            return JSONResponse(content={'error': '[server] auth info is required'}, status_code=401)

        # Validate credentials
        if is_api_key_valid(api_key, api_secret):
            # Handle aysnc vs sync route handlers
            if iscoroutinefunction(func):
                return await func(request, *args, **kwargs)  # Await the async route function
            else:
                return func(request, *args, **kwargs)
        return JSONResponse(content={'error': 'Invalid API Key'}, status_code=401)

    return wrapper


def retry(count, exceptions, delay=0.5):
    """
    Retry decorator, will attempt to run functions w/ certain delay.
    """
    def decorator(func):
        def newfn(*args, **kwargs):
            attempt = 0
            while attempt < count:
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    logging.error(f"Except occured when running '{func}', attempt {attempt} of {count}")
                    attempt += 1
                    time.sleep(delay)
            return func(*args, **kwargs)
        return newfn
    return decorator


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
