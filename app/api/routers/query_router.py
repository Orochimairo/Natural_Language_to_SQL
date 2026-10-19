"""问数查询接口路由。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from app.api.dependencies import get_query_service
from app.api.schemas.query_schema import QuerySchema
from app.services.query_service import QueryService

query_router = APIRouter()


@query_router.post("/api/query")
async def query_handler(
    request: QuerySchema,
    query_service: Annotated[
        QueryService,
        Depends(get_query_service),
    ],
) -> StreamingResponse:
    """接收自然语言问题并返回真实问数 SSE 流。"""

    return StreamingResponse(
        query_service.query(request.query),
        media_type="text/event-stream",
    )
