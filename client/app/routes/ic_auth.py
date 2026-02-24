import json
import os
import requests
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from colorlog import getLogger
from app.tools.service_helper import api_auth_required


logger = getLogger('main')

ic_auth_router = APIRouter(prefix='/ic_auth/api/v1', tags=['xflow'])

# Response type-forcing & validation
class CreateTicketRequest(BaseModel):
    creator: str = Field(description="Request user")
    data: dict = Field(description="Request form data")


@ic_auth_router.post("/create_ticket")
@api_auth_required
async def create_ticket(
    request: Request,
    body: CreateTicketRequest
):
    is_success = False
    msg = "NA"
    ticket_id = None
    try:
        _host = os.environ.get("SERVER_HOST")
        _port = os.environ.get("SERVER_PORT")
        app_id = os.environ.get('LARK_APP_ID')
        app_secret = os.environ.get('LARK_APP_SECRET')

        headers = {
            "x-app-id": app_id,
            "x-app-secret": app_secret,
            "Content-Type": "application/json"
        }

        data = {
            "creator": body.creator,
            "data": body.data
        }

        request_url = f"http://{_host}:{_port}/ic_auth/api/v1/create_ticket"
        resp = requests.post(url=request_url, headers=headers, json=data)


        resp_json = resp.json()
        if "is_success" not in resp_json:
            logger.error(f"Failed to create ticket: {resp_json} | error code: {resp.status_code}")

        is_success = resp_json['is_success']
        msg = resp_json['message']
        ticket_id = resp_json['ticket_id']

        return {"is_success": is_success, "message": msg, "ticket_id": ticket_id}

    except Exception as e:
        logger.error(f"Client request failed: {e}", exc_info=True)
        return {"is_success": False, "message": str(e), "ticket_id": None}

