"""字段召回节点集成检查。"""

import asyncio
from copy import deepcopy
from typing import cast

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.recall_column import (
    recall_column,
)
from app.agent.state import DataAgentState
from app.clients.embedding_client_manager import (
    embedding_client_manager,
)
from app.clients.qdrant_client_manager import (
    qdrant_client_manager,
)
from app.repositories.qdrant.column_qdrant_repository import (
    ColumnQdrantRepository,
)


async def main() -> None:
    """使用真实 LLM、TEI 和 Qdrant 检查字段召回。"""

    qdrant_client_manager.init()
    embedding_client_manager.init()

    try:
        context = cast(
            DataAgentContext,
            {
                "embedding_client": (embedding_client_manager.client),
                "column_qdrant_repository": (
                    ColumnQdrantRepository(qdrant_client_manager.client)
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

        result = await recall_column(
            state,
            runtime,
        )

        expected_events = [
            {
                "type": "progress",
                "step": "召回字段信息",
                "status": "running",
            },
            {
                "type": "progress",
                "step": "召回字段信息",
                "status": "success",
            },
        ]

        if events != expected_events:
            raise AssertionError(f"字段召回事件不正确: {events}")

        retrieved_column_infos = result.get("retrieved_column_infos")

        if not isinstance(
            retrieved_column_infos,
            list,
        ):
            raise AssertionError(f"节点没有返回字段列表: {result}")

        if not retrieved_column_infos:
            raise AssertionError("没有召回任何字段")

        if state != original_state:
            raise AssertionError("字段召回节点修改了输入 State")

        print("字段召回事件:", events)

        for column_info in retrieved_column_infos:
            print(
                column_info.id,
                column_info.name,
                column_info.table_id,
            )

        print("输入 State 未被修改")
        print("字段召回节点检查通过")
    finally:
        await embedding_client_manager.close()
        await qdrant_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
