"""FastAPI 应用生命周期管理。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.clients.embedding_client_manager import (
    embedding_client_manager,
)
from app.clients.es_client_manager import (
    es_client_manager,
)
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import (
    qdrant_client_manager,
)


@asynccontextmanager
async def lifespan(
    _app: FastAPI,
) -> AsyncIterator[None]:
    """初始化并释放应用级外部客户端。"""

    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()

    try:
        yield
    finally:
        await dw_mysql_client_manager.close()
        await meta_mysql_client_manager.close()
        await es_client_manager.close()
        await embedding_client_manager.close()
        await qdrant_client_manager.close()
