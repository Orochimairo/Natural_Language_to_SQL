"""M5 三路召回图级集成检查。"""

import asyncio

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.state import DataAgentState
from app.clients.embedding_client_manager import (
    embedding_client_manager,
)
from app.clients.es_client_manager import es_client_manager
from app.clients.qdrant_client_manager import (
    qdrant_client_manager,
)
from app.repositories.es.value_es_repository import (
    ValueESRepository,
)
from app.repositories.qdrant.column_qdrant_repository import (
    ColumnQdrantRepository,
)
from app.repositories.qdrant.metric_qdrant_repository import (
    MetricQdrantRepository,
)


async def main() -> None:
    """使用真实依赖运行图，并检查三路召回写回的状态。"""

    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()

    try:
        context = DataAgentContext(
            embedding_client=embedding_client_manager.client,
            column_qdrant_repository=ColumnQdrantRepository(
                qdrant_client_manager.client
            ),
            metric_qdrant_repository=MetricQdrantRepository(
                qdrant_client_manager.client
            ),
            value_es_repository=ValueESRepository(es_client_manager.client),
        )

        state: DataAgentState = {
            "query": "华东地区 iPhone 的销售总额是多少？",
            "keywords": [],
            "retrieved_column_infos": [],
            "retrieved_metric_infos": [],
            "retrieved_value_infos": [],
            "error": None,
        }

        result = await graph.ainvoke(
            input=state,
            context=context,
        )

        print(
            "字段:",
            [column_info.id for column_info in result["retrieved_column_infos"]],
        )
        print(
            "指标:",
            [metric_info.id for metric_info in result["retrieved_metric_infos"]],
        )
        print(
            "字段值:",
            [
                (
                    value_info.value,
                    value_info.column_id,
                )
                for value_info in result["retrieved_value_infos"]
            ],
        )
    finally:
        await es_client_manager.close()
        await embedding_client_manager.close()
        await qdrant_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
