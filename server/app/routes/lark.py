from types import NoneType
from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
import json
from pydantic.networks import HttpUrl
from app.db.base import get_db, Message
from app.services.lark_service import LarkAPIModule, ServiceException
from app.tools.service_helper import api_auth_required
from logging import getLogger

logger = getLogger("main")

lark_router = APIRouter(prefix='/lark/api/v1', tags=['lark'])


# Respone type-forcing & validation
class ChatIdRequest(BaseModel):
    name: str = Field(
        ...,
        max_length=2048,
        description="Chat name (maximum 2048 characters)"
    )
    trace_id: Optional[str] = Field(
        description="Trace ID for request.",
        example="1234567890"
    )

class ChatIdFeedRequest(BaseModel):
    id: str = Field(
        ...,
        max_length=2048,
        description="19-digit feed id (left for historical reason)"
    )
    trace_id: Optional[str] = Field(
        description="Trace ID for request.",
        example="1234567890"
    )


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
    sender: str
    recipients: list[str]
    header_color: str = "green"
    trace_id: Optional[str] = Field(
        description="Trace ID for request.",
        example="1234567890"
    )


class CardMessageRequest(BaseModel):
    card_id: str
    content: str = Field(
        ...,
        max_length=2048,
        description="Message content (maximum 2048 characters)"
    )  # Returns 422 Validation Error
    sender: str
    recipients: list[str]
    trace_id: Optional[str] = Field(
        None,
        description="Trace ID for request.",
        example="1234567890"
    )


@lark_router.get("/get_chat_id", description="Search for chat_id from chat name.")
async def get_chat_id(
    request: Request,
    body: ChatIdRequest,
    domain: str = Query(default="picoheart", description="Feishu domain (default: picoheart)")
):
    async with request.app.state.semaphore:
        _code = 500
        msg = 'un-processed request'
        try:
            client = LarkAPIModule(domain=domain)
            logger.debug(f"Search chat_id request: {body.model_dump()} | domain: {domain} | Trace ID: {body.trace_id}")
            
            ret_code, data, msg = client.search_chat_id(body.name)
        except Exception as e:
            logger.error(f"Client request failed: {e}", exc_info=True)
            return {'return_code': 504, 'message': str(e), 'data': []}
        else:
            logger.debug(f"Search chat_id response: {ret_code} | {msg} | {data}")
            return {'return_code': 0, 'message': 'success', 'data': data}


@lark_router.get("/get_chat_id_from_feed", description="Search for chat_id from chat name.")
async def get_chat_id_from_feed(
    request: Request,
    body: ChatIdFeedRequest,
    domain: str = Query(default="picoheart", description="Feishu domain (default: picoheart)")
):
    async with request.app.state.semaphore:
        _code = 500
        msg = 'un-processed request'
        try:
            client = LarkAPIModule(domain=domain)
            logger.debug(f"get_chat_id_from_feed request: {body.model_dump()} | domain: {domain} | Trace ID: {body.trace_id}")
            
            ret_code, data, msg = client.search_chat_id_from_feed(body.id)
        except Exception as e:
            logger.error(f"Client request failed: {e}", exc_info=True)
            return {'return_code': 504, 'message': str(e), 'data': []}
        else:
            logger.debug(f"get_chat_id_from_feed response: {ret_code} | {msg} | {data}")
            return {'return_code': 0, 'message': 'success', 'data': data}


@lark_router.post("/send_lark_msg", description="Send a Lark message.")
@api_auth_required
async def send_lark_msg(
    request: Request,
    body: MessageRequest,
    domain: str = Query(default="picoheart", description="Feishu domain (default: picoheart)"),
    db: Session = Depends(get_db)
):
    try:
        async with request.app.state.semaphore:
            _code = 500
            msg = "un-processed request"
            warn_msg = ""
            try:
                client = LarkAPIModule(domain=domain)
                logger.debug(f"Message request: {body.sender} | Request body: {body.model_dump()} | domain: {domain} | Trace ID: {body.trace_id}")

                receive_ids, chat_id = client.process_recipients(body.recipients)

                logger.debug(f"Receive ids: {receive_ids} | Chat id: {chat_id}")
                
                if len(receive_ids) == 1:
                    _code, _, msg = client.send_message(
                        receive_id=receive_ids[0],
                        content=body.content,
                        title=body.title,
                        title_color=body.header_color,
                        msg_type='standard'
                    )
                    if _code == 0:
                        logger.debug(f"trace id: {body.trace_id} | Message sent to {receive_ids[0]}")
                    else:
                        logger.error(f"trace id: {body.trace_id} | Message failed to send to {receive_ids} | {msg}")
                else:
                    try:  
                        _code, open_id_info, msg = client.get_batch_user_id(receive_ids)  # emails to open_id

                        if _code != 0:
                            logger.error(f"trace id: {body.trace_id} | Failed to convert emails to open_ids: {receive_ids} | {msg}")
                            return {'return_code': 504, 'message': msg, 'trace_id': body.trace_id}
                        else:
                            open_ids = list(map(lambda x: x.get('user_id'), open_id_info))
                            logger.debug(f"[send_lark_msg] Converted emails {receive_ids} to open_ids: {open_ids}")

                            logger.debug(f"[send_lark_msg.before_warn] open_ids: {open_ids}")
                            if any(_id is None for _id in open_ids):  # Invalid open_ids  
                                warn_msg = f"Invalid open_ids: {open_ids} from {receive_ids}"
                                logger.warning(warn_msg)
                                open_ids = [id for id in open_ids if id is not None]  # Keep valid ids
                            logger.debug(f"[send_lark_msg.after_warn] open_ids: {open_ids}")

                            _code, _, msg = client.batch_send_message(
                                open_ids=open_ids,
                                content=body.content,
                                title=body.title,
                                title_color=body.header_color,
                                msg_type='standard'
                            )
                            if _code == 0:
                                logger.debug(f"trace id: {body.trace_id} | Message sent to {body.recipients}")
                            else:
                                logger.error(f"trace id: {body.trace_id} | Message failed to send to {receive_ids} | {msg}")
                    except Exception as e:
                        logger.error(f"batch_send message failed: {e}", exc_info=True)
                        return {'return_code': 504, 'message': str(e), 'trace_id': body.trace_id}

                if chat_id:
                    _code, _, msg = client.send_message(
                        receive_id=chat_id,
                        receive_id_type='chat_id',
                        content=body.content,
                        title=body.title,
                        title_color=body.header_color,
                        msg_type='standard'
                    )
                    if _code == 0:
                        logger.debug(f"trace id: {body.trace_id} | Message sent to {chat_id}")
                    else:
                        logger.error(f"trace id: {body.trace_id} | Message failed to send to chat {chat_id} | {msg}")
                # else:
                #     return {'return_code': 504, 'message': 'Un-supported usage.', 'trace_id': body.trace_id}
            except ServiceException as e:
                logger.error(f"Client request failed: {e}", exc_info=True)
                return {'return_code': 504, 'message': str(e), 'trace_id': body.trace_id}

            except Exception as e:
                logger.error(f"Client request failed: {e}", exc_info=True)
                db_request = Message(
                    trace_id=body.trace_id,
                    username=body.sender,
                    recipient=''.join(body.recipients),
                    content=str(body.model_dump()),
                    result=f"code {_code}: {msg}"
                )
                db.add(db_request)
                db.commit()
                return {'return_code': 504, 'message': str(e), 'trace_id': body.trace_id}

            else:
                if warn_msg:  
                    msg += warn_msg

                db_request = Message(
                    trace_id=body.trace_id,
                    username=body.sender,
                    recipient=''.join(body.recipients),
                    content=str(body.model_dump()),
                    result=f"code {_code}: {msg}"
                )
                db.add(db_request)
                db.commit()
                return {'return_code': _code, 'message': msg, 'trace_id': body.trace_id}
    except Exception as e:
        logger.error(f"Client request failed: {e}", exc_info=True)
        return {'return_code': 504, 'message': str(e), 'trace_id': body.trace_id}


@lark_router.post("/send_card", description="Send a Lark card message.")
@api_auth_required
async def send_card(
    request: Request,
    body: CardMessageRequest,
    domain: str = Query(default="picoheart", description="Feishu domain (default: picoheart)"),
    db: Session = Depends(get_db)
):
    async with request.app.state.semaphore:
        msg = "un-processed request"
        _code = 500
        warn_msg = ""  
        try:
            client = LarkAPIModule(domain=domain)
            logger.debug(f"Message request: {body.sender} | Request body: {body.model_dump()} | domain: {domain} | Trace ID: {body.trace_id}")
            receive_ids, chat_id = client.process_recipients(body.recipients)

            if len(receive_ids) == 1:
                _code, _, msg = client.send_message(
                    receive_id=receive_ids[0],
                    template_variables=json.loads(body.content),
                    template_id=body.card_id,
                    msg_type='interactive'
                )

                if _code != 0:
                    logger.error(f"trace id: {body.trace_id} | Failed to send card message {receive_ids[0]}.")
                else:
                    logger.debug(f"trace id: {body.trace_id} | Card message sent to {receive_ids[0]}")
            else:
                _code, open_id_info, msg = client.get_batch_user_id(receive_ids)  # emails to open_id

                if _code != 0:
                    logger.error(f"trace id: {body.trace_id} | Failed to convert emails to open_ids: {receive_ids} | {msg}")
                    return {'return_code': 504, 'message': msg, 'trace_id': body.trace_id}
                else:
                    open_ids = list(map(lambda x: x.get('user_id'), open_id_info))
                    logger.debug(f"[send_card] Converted emails {receive_ids} to open_ids: {open_ids}")

                    if any(_id is None for _id in open_ids):  # Invalid open_ids  
                        warn_msg = f"Invalid open_ids: {open_ids} from {receive_ids}"
                        open_ids = [id for id in open_ids if id is not None]  # Keep valid ids

                try: 
                    _code, _, msg = client.batch_send_message(
                        open_ids=open_ids,
                        template_variables=json.loads(body.content),
                        template_id=body.card_id,
                        msg_type="interactive"
                    )

                    if _code == 0:
                        logger.debug(f"trace id: {body.trace_id} | Message sent to {body.recipients}")
                    else:
                        logger.error(f"trace id: {body.trace_id} | Message failed to send to {receive_ids} | {msg}")
                except Exception as e:
                    logger.error(f"batch_send message failed: {e}", exc_info=True)
                    return {'return_code': 504, 'message': str(e), 'trace_id': body.trace_id}

            if chat_id:  # group_chat
                _code, _, msg = client.send_message(
                    receive_id=chat_id,
                    receive_id_type='chat_id',
                    template_variables=json.loads(body.content),
                    template_id=body.card_id,
                    msg_type='interactive'
                )
                if _code != 0:
                    logger.error(f"trace id: {body.trace_id} | Failed to send card message chat {chat_id}")
                else:
                    logger.debug(f"trace id: {body.trace_id} | Card message sent to chat {chat_id}")
            # else:
            #     return {'return_code': 504, 'message': 'Un-supported usage.', 'trace_id': body.trace_id}

        except Exception as e:
            logger.error(f"Client request failed: {e}", exc_info=True)
            # try:
            db_request = Message(
                trace_id=body.trace_id,
                username=body.sender,
                recipient=''.join(body.recipients),
                content=str(body.model_dump()),
                result=f"504: {msg}"
            )
            db.add(db_request)
            db.commit()
            # except Exception as e:
            #     logger.error(f"Failed to commit db request: {e}", exc_info=True)

            return {'return_code': 504, 'message': str(e), 'trace_id': body.trace_id}

        else:
            if warn_msg:  
                msg += warn_msg

            db_request = Message(
                trace_id=body.trace_id,
                username=body.sender,
                recipient=''.join(body.recipients),
                content=str(body.model_dump()),
                result=f"{_code}: {msg}"
            )
            db.add(db_request)
            db.commit()
            return {'return_code': _code, 'message': msg, 'trace_id': body.trace_id}


@lark_router.get("/test_asyncio", description="Async sleep to simulate client function call.")
async def sleep(request: Request):
    async with request.app.state.semaphore:
        try:
            client = LarkAPIModule()
            await client.sleep()
        except Exception as e:
            logger.error(f"Client request failed: {e}", exc_info=True)
            return {'is_success': False, 'message': str(e), 'trace_id': None}

        return {"is_success": True, 'message': "Slept for 1 sec.", "trace_id": None}
