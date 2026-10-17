"""字段值召回节点集成检查。"""

import asyncio
from typing import cast

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.recall_value import recall_value
from app.agent.state import DataAgentState
from app.clients.es_client_manager import es_client_manager
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

        result = await recall_value(state, runtime)

        for value_info in result["retrieved_value_infos"]:
            print(
                value_info.id,
                value_info.value,
                value_info.column_id,
            )
    finally:
        await es_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
