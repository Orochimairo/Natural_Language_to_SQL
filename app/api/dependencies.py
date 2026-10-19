"""FastAPI 查询接口依赖组装。"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.embedding_client_manager import (
    TEIEmbeddingClient,
    embedding_client_manager,
)
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import (
    qdrant_client_manager,
)
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
from app.services.query_service import QueryService


async def get_meta_session() -> AsyncIterator[AsyncSession]:
    """为一次请求提供元数据库 Session。"""

    async with meta_mysql_client_manager.session_factory() as session:
        yield session


async def get_meta_mysql_repository(
    session: Annotated[
        AsyncSession,
        Depends(get_meta_session),
    ],
) -> MetaMySQLRepository:
    """使用请求级 Session 创建元数据仓储。"""

    return MetaMySQLRepository(session)


async def get_embedding_client() -> TEIEmbeddingClient:
    """取得应用级 Embedding 客户端。"""

    return embedding_client_manager.client


async def get_dw_session() -> AsyncIterator[AsyncSession]:
    """为一次请求提供数仓 Session。"""

    async with dw_mysql_client_manager.session_factory() as session:
        yield session


async def get_dw_mysql_repository(
    session: Annotated[
        AsyncSession,
        Depends(get_dw_session),
    ],
) -> DWMySQLRepository:
    """使用请求级 Session 创建数仓仓储。"""

    return DWMySQLRepository(session)


async def get_column_qdrant_repository() -> ColumnQdrantRepository:
    """使用应用级 Qdrant 客户端创建字段仓储。"""

    return ColumnQdrantRepository(qdrant_client_manager.client)


async def get_metric_qdrant_repository() -> MetricQdrantRepository:
    """使用应用级 Qdrant 客户端创建指标仓储。"""

    return MetricQdrantRepository(qdrant_client_manager.client)


async def get_value_es_repository() -> ValueESRepository:
    """使用应用级 Elasticsearch 客户端创建字段值仓储。"""

    return ValueESRepository(es_client_manager.client)


async def get_query_service(
    meta_mysql_repository: Annotated[
        MetaMySQLRepository,
        Depends(get_meta_mysql_repository),
    ],
    embedding_client: Annotated[
        TEIEmbeddingClient,
        Depends(get_embedding_client),
    ],
    dw_mysql_repository: Annotated[
        DWMySQLRepository,
        Depends(get_dw_mysql_repository),
    ],
    column_qdrant_repository: Annotated[
        ColumnQdrantRepository,
        Depends(get_column_qdrant_repository),
    ],
    metric_qdrant_repository: Annotated[
        MetricQdrantRepository,
        Depends(get_metric_qdrant_repository),
    ],
    value_es_repository: Annotated[
        ValueESRepository,
        Depends(get_value_es_repository),
    ],
) -> QueryService:
    """组装一次问数请求需要的 QueryService。"""

    return QueryService(
        meta_mysql_repository=meta_mysql_repository,
        embedding_client=embedding_client,
        dw_mysql_repository=dw_mysql_repository,
        column_qdrant_repository=column_qdrant_repository,
        metric_qdrant_repository=metric_qdrant_repository,
        value_es_repository=value_es_repository,
    )
