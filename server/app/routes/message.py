from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import and_, between
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.base import get_db, Message

router = APIRouter(prefix="/messages/api/v1", tags=["消息查询"])

@router.get("/search", summary="多条件查询消息记录")
def query_messages(
    db: Session = Depends(get_db),
    trace_id: str = Query(None, description="按trace_id精确查询"),
    username: str = Query(None, description="按username精确查询"),
    result_keyword: str = Query(None, description="按result内容模糊查询"),
    start_time: datetime = Query(None, description="created_at起始时间（格式：2024-01-01T00:00:00）"),
    end_time: datetime = Query(None, description="created_at结束时间（格式：2024-01-02T23:59:59）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    # 构建查询条件
    filters = []
    if trace_id: filters.append(Message.trace_id == trace_id)
    if username: filters.append(Message.username == username)
    if result_keyword: filters.append(Message.result.like(f"%{result_keyword}%"))
    if start_time and end_time: filters.append(between(Message.created_at, start_time, end_time))

    # 执行查询（带分页）
    query = db.query(Message)
    if filters: query = query.filter(and_(*filters))
    total = query.count()
    messages = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [{
            "trace_id": msg.trace_id,
            "username": msg.username,
            "recipient": msg.recipient,
            "content": msg.content,
            "result": msg.result,
            "created_at": msg.created_at.isoformat()
        } for msg in messages]
    }