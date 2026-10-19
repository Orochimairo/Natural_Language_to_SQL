"""指标召回节点集成检查。"""

import asyncio
from copy import deepcopy
from typing import cast

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.recall_metric import (
    recall_metric,
)
from app.agent.state import DataAgentState
from app.clients.embedding_client_manager import (
    embedding_client_manager,
)
from app.clients.qdrant_client_manager import (
    qdrant_client_manager,
)
from app.repositories.qdrant.metric_qdrant_repository import (
    MetricQdrantRepository,
)


async def main() -> None:
    """使用真实 LLM、TEI 和 Qdrant 检查指标召回。"""

    qdrant_client_manager.init()
    embedding_client_manager.init()

    try:
        context = cast(
            DataAgentContext,
            {
                "embedding_client": (embedding_client_manager.client),
                "metric_qdrant_repository": (
                    MetricQdrantRepository(qdrant_client_manager.client)
                ),
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

        result = await recall_metric(
            state,
            runtime,
        )

        expected_events = [
            {
                "type": "progress",
                "step": "召回指标信息",
                "status": "running",
            },
            {
                "type": "progress",
                "step": "召回指标信息",
                "status": "success",
            },
        ]

        if events != expected_events:
            raise AssertionError(f"指标召回事件不正确: {events}")

        retrieved_metric_infos = result.get("retrieved_metric_infos")

        if not isinstance(
            retrieved_metric_infos,
            list,
        ):
            raise AssertionError(f"节点没有返回指标列表: {result}")

        if not retrieved_metric_infos:
            raise AssertionError("没有召回任何指标")

        if state != original_state:
            raise AssertionError("指标召回节点修改了输入 State")

        print("指标召回事件:", events)

        for metric_info in retrieved_metric_infos:
            print(
                metric_info.id,
                metric_info.name,
                metric_info.relevant_columns,
            )

        print("输入 State 未被修改")
        print("指标召回节点检查通过")
    finally:
        await embedding_client_manager.close()
        await qdrant_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
