from fastapi import Request, HTTPException
from limits import limits, storage
from limits.strategies import FixedWindowRateLimiter
from app.core.config import settings

# Setup rate limiting
redis_storage = storage.RedisStorage(settings.REDIS_URL)


def rate_limit_middleware(max_requests: str, user_header: str = "X-User-ID"):
    def decorator(func):
        @limits(
            calls=int(max_requests.split('/')[0]),
            period=max_requests.split('/')[1],
            storage_uri=settings.REDIS_URL,
            key_func=lambda request: f"{request.headers.get(user_header)}:{request.url.path}"
        )
        async def wrapper(request: Request, *args, **kwargs):
            # Get user identifier from header
            user_id = request.headers.get(user_header)
            if not user_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required header: {user_header}"
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator