"""FastAPI 真实查询接口功能检查。"""

import json

from fastapi.testclient import TestClient

from main import app


def main() -> None:
    """通过应用内 HTTP 请求检查真实查询接口。"""

    payload = {
        "query": "华东地区 iPhone 的销售总额是多少？",
    }

    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/query",
            json=payload,
        ) as response:
            if response.status_code != 200:
                raise AssertionError(f"查询接口状态码不正确: {response.status_code}")

            content_type = response.headers.get(
                "content-type",
                "",
            )

            if not content_type.startswith("text/event-stream"):
                raise AssertionError(f"查询接口响应类型不正确: {content_type}")

            lines = [line for line in response.iter_lines() if line]

        invalid_response = client.post(
            "/api/query",
            json={},
        )

    if invalid_response.status_code != 422:
        raise AssertionError(
            f"缺少 query 的请求没有返回 422: {invalid_response.status_code}"
        )

    if not lines:
        raise AssertionError("查询接口没有返回 SSE 消息")

    events: list[dict] = []

    for line in lines:
        if not line.startswith("data: "):
            raise AssertionError(f"SSE 消息没有 data 前缀: {line}")

        event = json.loads(line.removeprefix("data: "))

        if not isinstance(event, dict):
            raise AssertionError(f"SSE 数据不是 JSON 对象: {event}")

        events.append(event)

    error_events = [event for event in events if event.get("type") == "error"]

    if error_events:
        raise AssertionError(f"查询接口返回错误事件: {error_events}")

    progress_events = [event for event in events if event.get("type") == "progress"]

    result_events = [event for event in events if event.get("type") == "result"]

    if not progress_events:
        raise AssertionError("查询接口没有返回进度事件")

    if len(result_events) != 1:
        raise AssertionError(f"查询接口应该返回一个结果事件，实际为: {result_events}")

    progress_steps = {event.get("step") for event in progress_events}

    if "抽取关键词" not in progress_steps:
        raise AssertionError(f"进度中缺少抽取关键词: {progress_steps}")

    if "执行SQL" not in progress_steps:
        raise AssertionError(f"进度中缺少执行SQL: {progress_steps}")

    query_result = result_events[0].get("data")

    if not isinstance(query_result, list):
        raise AssertionError(f"最终查询结果不是列表: {query_result}")

    if not query_result:
        raise AssertionError("最终查询结果为空")

    if not isinstance(query_result[0], dict):
        raise AssertionError(f"查询结果行不是字典: {query_result[0]}")

    print("HTTP 状态码:", response.status_code)
    print("响应类型:", content_type)
    print("进度事件数量:", len(progress_events))
    print("最终结果事件:", result_events[0])
    print(
        "缺少 query 的请求状态码:",
        invalid_response.status_code,
    )
    print("FastAPI 真实查询接口检查通过")


if __name__ == "__main__":
    main()
