"""问数智能体的运行时上下文。"""

from typing import TypedDict

from app.clients.embedding_client_manager import (
    TEIEmbeddingClient,
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


class DataAgentContext(TypedDict):
    """保存节点运行时需要的外部依赖。"""

    embedding_client: TEIEmbeddingClient
    column_qdrant_repository: ColumnQdrantRepository
    metric_qdrant_repository: MetricQdrantRepository
    value_es_repository: ValueESRepository
