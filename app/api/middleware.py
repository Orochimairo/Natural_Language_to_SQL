"""FastAPI 请求中间件。"""

from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import (
    ASGIApp,
    Message,
    Receive,
    Scope,
    Send,
)

from app.core.context import request_id_ctx_var


class RequestIDMiddleware:
    """为每次 HTTP 请求提供独立 request_id。"""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """设置请求上下文并在响应结束后恢复。"""

        if scope["type"] != "http":
            await self.app(
                scope,
                receive,
                send,
            )
            return

        request_id = uuid4().hex
        token = request_id_ctx_var.set(request_id)

        async def send_with_request_id(
            message: Message,
        ) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(
                    scope=message,
                )
                headers.append(
                    "X-Request-ID",
                    request_id,
                )

            await send(message)

        try:
            await self.app(
                scope,
                receive,
                send_with_request_id,
            )
        finally:
            request_id_ctx_var.reset(token)
