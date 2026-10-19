"""字段值召回节点集成检查。"""

import asyncio
from copy import deepcopy
from typing import cast

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.recall_value import recall_value
from app.agent.state import DataAgentState
from app.clients.es_client_manager import (
    es_client_manager,
)
from app.repositories.es.value_es_repository import (
    ValueESRepository,
)


async def main() -> None:
    """使用真实 LLM 和 Elasticsearch 检查字段值召回。"""

    es_client_manager.init()

    try:
        context = cast(
            DataAgentContext,
            {
                "value_es_repository": ValueESRepository(es_client_manager.client),
            },
        )

        events: list[dict[str, str]] = []

        runtime = Runtime[DataAgentContext](
            context=context,
            stream_writer=events.append,
        )

        state: DataAgentState = {
            "query": ("华东地区 iPhone 的销售总额是多少？"),
            "keywords": [
                "iPhone",
                "销售总额",
                "华东地区",
            ],
            "retrieved_column_infos": [],
            "retrieved_metric_infos": [],
            "retrieved_value_infos": [],
            "error": None,
        }
        original_state = deepcopy(state)

        result = await recall_value(
            state,
            runtime,
        )

        expected_events = [
            {
                "type": "progress",
                "step": "召回字段取值",
                "status": "running",
            },
            {
                "type": "progress",
                "step": "召回字段取值",
                "status": "success",
            },
        ]

        if events != expected_events:
            raise AssertionError(f"字段值召回事件不正确: {events}")

        retrieved_value_infos = result.get("retrieved_value_infos")

        if not isinstance(
            retrieved_value_infos,
            list,
        ):
            raise AssertionError(f"节点没有返回字段值列表: {result}")

        if not retrieved_value_infos:
            raise AssertionError("没有召回任何字段值")

        if state != original_state:
            raise AssertionError("字段值召回节点修改了输入 State")

        print("字段值召回事件:", events)

        for value_info in retrieved_value_infos:
            print(
                value_info.id,
                value_info.value,
                value_info.column_id,
            )

        print("输入 State 未被修改")
        print("字段值召回节点检查通过")
    finally:
        await es_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
