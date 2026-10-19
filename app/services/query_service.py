"""问数查询服务。"""

import json
from collections.abc import AsyncIterator

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.state import DataAgentState
from app.clients.embedding_client_manager import TEIEmbeddingClient
from app.repositories.es.value_es_repository import (
    ValueESRepository,
)
from app.repositories.mysql.dw.dw_mysql_repository import (
    DWMySQLRepository,
)
from app.repositories.mysql.meta.meta_mysql_repository import (
    MetaMySQLRepository,
)
from app.repositories.qdrant.column_qdrant_repository import (
    ColumnQdrantRepository,
)
from app.repositories.qdrant.metric_qdrant_repository import (
    MetricQdrantRepository,
)


class QueryService:
    """执行问数工作流并输出 SSE 消息。"""

    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        embedding_client: TEIEmbeddingClient,
        dw_mysql_repository: DWMySQLRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        metric_qdrant_repository: MetricQdrantRepository,
        value_es_repository: ValueESRepository,
    ):
        self.meta_mysql_repository = meta_mysql_repository
        self.embedding_client = embedding_client
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.value_es_repository = value_es_repository

    async def query(
        self,
        query: str,
    ) -> AsyncIterator[str]:
        """运行一次问数工作流并逐条输出 SSE 消息。"""

        state: DataAgentState = {
            "query": query,
            "keywords": [],
            "retrieved_column_infos": [],
            "retrieved_metric_infos": [],
            "retrieved_value_infos": [],
            "table_infos": [],
            "metric_infos": [],
            "date_info": {
                "date": "",
                "weekday": "",
                "quarter": "",
            },
            "db_info": {
                "dialect": "",
                "version": "",
            },
            "sql": "",
            "error": None,
        }

        context = DataAgentContext(
            embedding_client=self.embedding_client,
            column_qdrant_repository=self.column_qdrant_repository,
            metric_qdrant_repository=self.metric_qdrant_repository,
            value_es_repository=self.value_es_repository,
            meta_mysql_repository=self.meta_mysql_repository,
            dw_mysql_repository=self.dw_mysql_repository,
        )

        try:
            async for chunk in graph.astream(
                input=state,
                context=context,
                stream_mode="custom",
            ):
                if isinstance(chunk, str):
                    event = {
                        "type": "progress",
                        "step": chunk,
                        "status": "running",
                    }
                elif isinstance(chunk, dict):
                    event = chunk
                else:
                    raise TypeError(
                        "LangGraph 自定义流只允许输出字符串或字典，"
                        f"实际类型为 {type(chunk).__name__}"
                    )

                data = json.dumps(
                    event,
                    ensure_ascii=False,
                    default=str,
                )
                yield f"data: {data}\n\n"
        except Exception as error:
            event = {
                "type": "error",
                "message": str(error),
            }
            data = json.dumps(
                event,
                ensure_ascii=False,
                default=str,
            )
            yield f"data: {data}\n\n"
