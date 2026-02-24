import json
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from colorlog import getLogger
from app.tools.service_helper import api_auth_required
from app.services.xflow_service_client import XflowServiceClient


logger = getLogger('main')

xflow_router = APIRouter(prefix='/xflow/api/v1', tags=['xflow'])

# Response type-forcing & validation
class CreateTicketRequest(BaseModel):
    request_user: str = Field(description="Request user")
    process_name: str = Field(description="Process name")
    variables: dict = Field(description="Variables")


@xflow_router.post("/create_ticket")
@api_auth_required
async def create_ticket(
    request: Request,
    body: CreateTicketRequest
):
    client = XflowServiceClient()
    try:
        is_success, msg, ticket_id, trace_id = client.create_ticket(
            request_user=body.request_user,
            process_name=body.process_name,
            variables=body.variables
        )

    except Exception as e:
        logger.error(f"Client request failed: {e}", exc_info=True)
        return {"is_success": False, "message": str(e), "ticket_id": {None}, 'trace_id': None}
    
    return {"is_success": is_success, "message": msg, "ticket_id": ticket_id, "trace_id": trace_id}
