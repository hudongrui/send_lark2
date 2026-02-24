import json
import requests
import os
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from colorlog import getLogger
from app.tools.service_helper import api_auth_required


logger = getLogger('main')

meego_router = APIRouter(prefix='/meego/api/v1', tags=['xflow'])

class ProjectConfigRequest(BaseModel):
    project: str = Field(description="Requested project name")

@meego_router.get("/get_project_layout")
@api_auth_required
async def create_ticket(
    request: Request,
    body: ProjectConfigRequest
):

    _host = os.environ.get("SERVER_HOST")
    _port = os.environ.get("SERVER_PORT")

    service_url = f"http://{_host}:{_port}"
    headers = {
        "app-id": os.environ.get('LARK_APP_ID'),
        "app-secret": os.environ.get('LARK_APP_SECRET'),
        "Content-Type": "application/json"
    }
    try:
        request_url = f"{service_url}/meego/api/v1/get_project_layout"
        resp = requests.get(url=request_url, headers=headers)

    except Exception as e:
        logger.error(f"Client request failed: {e}", exc_info=True)
        return {"code": 500, "message": str(e), "data": None}
    
    if resp.status_code != 200:
        return {"code": resp.status_code, "message": resp.text, "data": None}
    else:
        return {"code": 0, "message": "ok", "data": resp.json()['data']}
