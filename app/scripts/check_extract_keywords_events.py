"""关键词抽取节点进度事件功能检查。"""

import asyncio
from copy import deepcopy
from typing import cast

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.extract_keywords import (
    extract_keywords,
)
from app.agent.state import DataAgentState


async def main() -> None:
    """检查成功和失败时的进度事件。"""

    events: list[dict[str, str]] = []

    runtime = Runtime[DataAgentContext](
        context=cast(
            DataAgentContext,
            {},
        ),
        stream_writer=events.append,
    )

    state = cast(
        DataAgentState,
        {
            "query": ("华东地区 iPhone 的销售总额是多少？"),
            "keywords": [],
        },
    )
    original_state = deepcopy(state)

    result = await extract_keywords(
        state,
        runtime,
    )

    expected_success_events = [
        {
            "type": "progress",
            "step": "抽取关键词",
            "status": "running",
        },
        {
            "type": "progress",
            "step": "抽取关键词",
            "status": "success",
        },
    ]

    if events != expected_success_events:
        raise AssertionError(f"成功事件顺序不正确: {events}")

    keywords = result.get("keywords")

    if not isinstance(keywords, list):
        raise AssertionError(f"节点没有返回关键词列表: {result}")

    if state["query"] not in keywords:
        raise AssertionError("关键词结果没有保留原始问题")

    if state != original_state:
        raise AssertionError("节点修改了输入 State")

    events.clear()

    invalid_state = cast(
        DataAgentState,
        {
            "query": "   ",
            "keywords": [],
        },
    )

    try:
        await extract_keywords(
            invalid_state,
            runtime,
        )
    except ValueError as error:
        if str(error) != "query 不能为空":
            raise AssertionError(f"错误信息不正确: {error}") from error
    else:
        raise AssertionError("空 query 没有抛出 ValueError")

    expected_error_events = [
        {
            "type": "progress",
            "step": "抽取关键词",
            "status": "running",
        },
        {
            "type": "progress",
            "step": "抽取关键词",
            "status": "error",
        },
    ]

    if events != expected_error_events:
        raise AssertionError(f"失败事件顺序不正确: {events}")

    print("成功事件:", expected_success_events)
    print("关键词:", keywords)
    print("失败事件:", expected_error_events)
    print("异常已继续抛出")
    print("关键词节点事件协议检查通过")


if __name__ == "__main__":
    asyncio.run(main())
