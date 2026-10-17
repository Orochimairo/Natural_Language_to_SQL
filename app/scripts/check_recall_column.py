"""字段召回节点集成检查。"""

import asyncio
from typing import cast

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.recall_column import recall_column
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

        runtime = Runtime[DataAgentContext](
            context=context,
            stream_writer=print,
        )

        state: DataAgentState = {
            "query": "华东地区 iPhone 的销售总额是多少？",
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

        result = await recall_column(state, runtime)

        for column_info in result["retrieved_column_infos"]:
            print(
                column_info.id,
                column_info.name,
                column_info.table_id,
            )
    finally:
        await embedding_client_manager.close()
        await qdrant_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
