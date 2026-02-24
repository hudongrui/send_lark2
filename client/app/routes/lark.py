from re import M
from fastapi import APIRouter, Request, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional
from pydantic.networks import HttpUrl
from app.services.message_service_client import MessageServiceClient, get_msg_client
from app.tools.service_helper import api_auth_required, generate_trace_id
from colorlog import getLogger


logger = getLogger("main")

lark_router = APIRouter(prefix='/lark/api/v1', tags=['lark'])

# Respone type-forcing & validation
class MessageRequest(BaseModel):
    title: str = Field(
        ...,
        max_length=2048,
        description="Title content (maximum 2048 characters)"
    )  # Returns 422 Validation Error
    content: str = Field(
        ...,
        max_length=2048,
        description="Message content (maximum 2048 characters)"
    )  # Returns 422 Validation Error
    recipients: list[str]
    header_color: str = "green"


class CardMessageRequest(BaseModel):
    card_id: str
    content: str = Field(
        ...,
        max_length=2048,
        description="Message content (maximum 2048 characters)"
    )  # Returns 422 Validation Error
    recipients: list[str]
    # webhook_url: Optional[HttpUrl] = Field(
    #     None,
    #     description="Lark BOT webhook url.",
    #     example="https://open.larkoffice.com/open-apis/bot/v2/hook/xxxx"
    # )

@lark_router.get("/get_chat_id_from_feed", description="Get Lark chat id from Feed ID.")
async def get_chat_id_from_feed(
    request: Request,
    id: str = Query(
        ...,
        max_length=2048,
        description="Chat name (maximum 2048 characters)"
    ),
    domain: str = Query(
        None,
        max_length=2048,
        description="Domain name (default: picoheart, accepts: bytedance)"
    )
):
    async with request.app.state.semaphore:
        trace_id = generate_trace_id()
        try:
            client = MessageServiceClient()
            logger.debug(f"Get chat_id_from_feed request: {id}")
            # Add await before client.send_message
            request_data = {
                "id": id,
                "trace_id": trace_id
            }
            # FIXME: Changed here.
            _code, _msg, trace_id = await client.get_chat_id_from_feed(request_data, domain=domain)
        except Exception as e:
            logger.error(f"Client request failed: {e}", exc_info=True)
            return {'return_code': 500, 'message': str(e), 'trace_id': trace_id}
        
        logger.debug(f"trace_id: {trace_id} | code: {_code} | message: {_msg}")
        return {'return_code': _code, 'message': _msg, 'trace_id': trace_id}


@lark_router.get("/get_chat_id", description="Get Lark chat id.")
async def get_chat_id(
    request: Request,
    name: str = Query(
        ...,
        max_length=2048,
        description="Chat name (maximum 2048 characters)"
    ),
    domain: str = Query(
        None,
        max_length=2048,
        description="Domain name (default: picoheart, accepts: bytedance)"
    )
):
    async with request.app.state.semaphore:
        trace_id = generate_trace_id()
        try:
            client = MessageServiceClient()
            logger.debug(f"Get chat_id request: {name}")
            # Add await before client.send_message
            request_data = {
                "name": name,
                "trace_id": trace_id
            }
            _code, _msg, trace_id = await client.get_chat_id(request_data, domain=domain)
        except Exception as e:
            logger.error(f"Client request failed: {e}", exc_info=True)
            return {'return_code': 500, 'message': str(e), 'trace_id': trace_id}
        
        logger.debug(f"trace_id: {trace_id} | code: {_code} | message: {_msg}")
        return {'return_code': _code, 'message': _msg, 'trace_id': trace_id}


@lark_router.post("/send_lark_msg", description="Send a Lark message.")
@api_auth_required
async def send_lark_msg(
    request: Request,
    body: MessageRequest,
    domain: str = Query(
        None,
        max_length=2048,
        description="Domain name (default: picoheart, accepts: bytedance)"
    )
):
    """
    request.headers = {
        "X-app-id": os.getenv('LARK_APP_ID'),
        "X-app-secret": os.getenv('LARK_APP_SECRET'),
        "X-username",
        "Content-type"
    }
    """
    async with request.app.state.semaphore:
        trace_id = generate_trace_id()
        try:
            sender = request.headers.get('X-username')
            client = MessageServiceClient()
            logger.debug(f"Message request: {sender} | Request body: {body.model_dump()}")
            # Add await before client.send_message
            request_data = body.model_dump()
            request_data.update(
                {
                    "sender": sender,
                    "trace_id": trace_id
                }
            )
            _code, _msg, trace_id = await client.send_message(request_data, domain=domain)
            # TODO: LOG RESULT
            # FIXME：处理请求体返回码
        except Exception as e:
            logger.error(f"Client request failed: {e}", exc_info=True)
            return {'return_code': 500, 'message': str(e), 'trace_id': body.trace_id}  # FIXME: 这个body 不会有trace_ide

        logger.debug(f"trace_id: {trace_id} | code: {_code} | message: {_msg}")
        return {'return_code': _code, 'message': _msg, 'trace_id': trace_id}


@lark_router.post("/send_card", description="Send a Lark card message.")
@api_auth_required
async def send_card(
    request: Request,
    body: CardMessageRequest,
    domain: str = Query(
        None,
        max_length=2048,
        description="Domain name (default: picoheart, accepts: bytedance)"
    )
):
    async with request.app.state.semaphore:
        trace_id = generate_trace_id()
        try:
            sender = request.headers.get('X-username')
            client = MessageServiceClient()
            logger.debug(f"Message request: {sender} | Request body: {body.model_dump()}")
            # Add await before client.send_message
            request_data = body.model_dump()
            request_data.update(
                {
                    "sender": sender,
                    "trace_id": trace_id
                }
            )
            _code, _msg, trace_id = await client.send_card(request_data, domain=domain)
        except Exception as e:
            logger.error(f"Client request failed: {e}", exc_info=True)
            return {'return_code': 500, 'message': str(e), 'trace_id': body.trace_id}

        logger.debug(f"trace_id: {trace_id} | code: {_code} | message: {_msg}")
        return {'return_code': _code, 'message': _msg, 'trace_id': trace_id}


@lark_router.get("/test_asyncio", description="Async sleep to simulate client function call.")
async def sleep(request: Request):
    async with request.app.state.semaphore:
        try:
            client = MessageServiceClient()
            await client.sleep()
        except Exception as e:
            logger.error(f"Client request failed: {e}", exc_info=True)
            return {'return_code': 400, 'message': str(e), 'trace_id': None}  # TODO: Generate trace_id here?

        return {'return_code': 0, 'message': "OK", "trace_id": None}