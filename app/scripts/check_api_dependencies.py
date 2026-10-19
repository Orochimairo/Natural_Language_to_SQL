"""FastAPI 查询依赖组装功能检查。"""

import asyncio

from app.api.dependencies import (
    get_column_qdrant_repository,
    get_dw_mysql_repository,
    get_dw_session,
    get_embedding_client,
    get_meta_mysql_repository,
    get_meta_session,
    get_metric_qdrant_repository,
    get_query_service,
    get_value_es_repository,
)
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
from app.services.query_service import QueryService


async def main() -> None:
    """检查所有依赖能否组装成 QueryService。"""

    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()

    meta_session_generator = get_meta_session()
    dw_session_generator = get_dw_session()

    try:
        meta_session = await anext(meta_session_generator)
        dw_session = await anext(dw_session_generator)

        meta_repository = await get_meta_mysql_repository(meta_session)
        dw_repository = await get_dw_mysql_repository(dw_session)
        embedding_client = await get_embedding_client()
        column_repository = await get_column_qdrant_repository()
        metric_repository = await get_metric_qdrant_repository()
        value_repository = await get_value_es_repository()

        query_service = await get_query_service(
            meta_mysql_repository=meta_repository,
            embedding_client=embedding_client,
            dw_mysql_repository=dw_repository,
            column_qdrant_repository=column_repository,
            metric_qdrant_repository=metric_repository,
            value_es_repository=value_repository,
        )

        if not isinstance(query_service, QueryService):
            raise AssertionError("没有成功创建 QueryService")

        if meta_repository.session is not meta_session:
            raise AssertionError("MetaMySQLRepository 没有使用元数据库 Session")

        if dw_repository.session is not dw_session:
            raise AssertionError("DWMySQLRepository 没有使用数仓 Session")

        if column_repository.client is not qdrant_client_manager.client:
            raise AssertionError("字段仓储没有使用 Qdrant Client")

        if metric_repository.client is not qdrant_client_manager.client:
            raise AssertionError("指标仓储没有使用 Qdrant Client")

        if value_repository.client is not es_client_manager.client:
            raise AssertionError("字段值仓储没有使用 Elasticsearch Client")

        if query_service.meta_mysql_repository is not meta_repository:
            raise AssertionError("元数据仓储没有注入 QueryService")

        if query_service.dw_mysql_repository is not dw_repository:
            raise AssertionError("数仓仓储没有注入 QueryService")

        if query_service.embedding_client is not embedding_client:
            raise AssertionError("Embedding Client 没有注入 QueryService")

        print("元数据库 Session 已创建")
        print("数仓 Session 已创建")
        print("Repository 已组装")
        print("QueryService:", type(query_service).__name__)
        print("FastAPI 依赖组装检查通过")
    finally:
        await meta_session_generator.aclose()
        await dw_session_generator.aclose()

        await dw_mysql_client_manager.close()
        await meta_mysql_client_manager.close()
        await es_client_manager.close()
        await embedding_client_manager.close()
        await qdrant_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
