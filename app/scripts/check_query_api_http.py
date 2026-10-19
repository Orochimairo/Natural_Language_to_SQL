"""通过真实 HTTP 检查问数接口和 SSE 响应。"""

import json
from time import monotonic

import httpx

API_URL = "http://127.0.0.1:8000/api/query"


def main() -> None:
    """模拟前端发送 POST 并逐条读取真实 SSE。"""

    payload = {
        "query": "华东地区 iPhone 的销售总额是多少？",
    }

    started_at = monotonic()
    events: list[dict] = []

    with httpx.stream(
        method="POST",
        url=API_URL,
        json=payload,
        timeout=120.0,
    ) as response:
        print("HTTP 状态码:", response.status_code)
        print(
            "响应类型:",
            response.headers.get("content-type"),
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "content-type",
            "",
        )

        if not content_type.startswith("text/event-stream"):
            raise AssertionError(f"响应类型不是 SSE: {content_type}")

        for line in response.iter_lines():
            if not line:
                continue

            elapsed = monotonic() - started_at

            if not line.startswith("data: "):
                raise AssertionError(f"SSE 消息格式错误: {line}")

            event = json.loads(line.removeprefix("data: "))

            if not isinstance(event, dict):
                raise AssertionError(f"SSE 数据不是 JSON 对象: {event}")

            events.append(event)

            print(
                f"{elapsed:.3f}s 收到 SSE:",
                event,
            )

    if not events:
        raise AssertionError("真实 HTTP 请求没有收到 SSE 事件")

    error_events = [event for event in events if event.get("type") == "error"]

    if error_events:
        raise AssertionError(f"查询接口返回错误事件: {error_events}")

    progress_events = [event for event in events if event.get("type") == "progress"]

    result_events = [event for event in events if event.get("type") == "result"]

    if not progress_events:
        raise AssertionError("没有收到进度事件")

    if len(result_events) != 1:
        raise AssertionError(f"预期一个结果事件，实际为: {result_events}")

    progress_steps = {event.get("step") for event in progress_events}

    if "抽取关键词" not in progress_steps:
        raise AssertionError(f"缺少抽取关键词事件: {progress_steps}")

    if "执行SQL" not in progress_steps:
        raise AssertionError(f"缺少执行SQL事件: {progress_steps}")

    query_result = result_events[0].get("data")

    if not isinstance(query_result, list):
        raise AssertionError(f"最终查询结果不是列表: {query_result}")

    if not query_result:
        raise AssertionError("最终查询结果为空")

    if not isinstance(query_result[0], dict):
        raise AssertionError(f"查询结果行不是字典: {query_result[0]}")

    print("进度事件数量:", len(progress_events))
    print("最终结果事件:", result_events[0])
    print("真实 HTTP POST、LangGraph 和 SSE 检查通过")


if __name__ == "__main__":
    main()
