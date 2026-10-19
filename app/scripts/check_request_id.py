"""FastAPI request_id 中间件功能检查。"""

import asyncio

import httpx

from app.core.context import request_id_ctx_var
from main import app


async def main() -> None:
    """并发请求应用并检查 request_id 隔离。"""

    check_path = "/_check/request-id"

    async def read_request_id() -> dict[str, str]:
        return {
            "request_id": request_id_ctx_var.get(),
        }

    app.add_api_route(
        path=check_path,
        endpoint=read_request_id,
        methods=["GET"],
        include_in_schema=False,
    )

    transport = httpx.ASGITransport(
        app=app,
    )

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        responses = await asyncio.gather(*[client.get(check_path) for _ in range(5)])

    request_ids: list[str] = []

    for response in responses:
        if response.status_code != 200:
            raise AssertionError(f"请求状态码不正确: {response.status_code}")

        header_request_id = response.headers.get("X-Request-ID")
        body_request_id = response.json().get("request_id")

        if not header_request_id:
            raise AssertionError("响应头缺少 X-Request-ID")

        if header_request_id != body_request_id:
            raise AssertionError(
                "响应头与请求上下文中的 "
                "request_id 不一致: "
                f"{header_request_id!r} != "
                f"{body_request_id!r}"
            )

        request_ids.append(header_request_id)

    if len(set(request_ids)) != len(request_ids):
        raise AssertionError(f"并发请求使用了重复 request_id: {request_ids}")

    restored_request_id = request_id_ctx_var.get()

    if restored_request_id != "1":
        raise AssertionError(f"请求结束后 ContextVar 没有恢复: {restored_request_id}")

    print("并发请求 request_id:")
    for request_id in request_ids:
        print(request_id)

    print(
        "请求结束后的默认 request_id:",
        restored_request_id,
    )
    print("FastAPI request_id 中间件检查通过")


if __name__ == "__main__":
    asyncio.run(main())
