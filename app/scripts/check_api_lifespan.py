"""FastAPI 应用生命周期功能检查。"""

from collections.abc import Callable

from fastapi.testclient import TestClient

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
from main import app


def assert_not_initialized(
    getter: Callable[[], object],
    resource_name: str,
) -> None:
    """确认资源已经恢复为未初始化状态。"""

    try:
        getter()
    except RuntimeError:
        return

    raise AssertionError(f"{resource_name} 在应用关闭后仍处于初始化状态")


def main() -> None:
    """启动并关闭 TestClient，检查 lifespan 两个阶段。"""

    with TestClient(app) as client:
        qdrant_client = qdrant_client_manager.client
        embedding_client = embedding_client_manager.client
        es_client = es_client_manager.client
        meta_engine = meta_mysql_client_manager.engine
        dw_engine = dw_mysql_client_manager.engine

        resources = [
            qdrant_client,
            embedding_client,
            es_client,
            meta_engine,
            dw_engine,
        ]

        if any(resource is None for resource in resources):
            raise AssertionError("应用启动后存在未初始化资源")

        response = client.post(
            "/api/query",
            json={
                "query": "华东地区销售额是多少？",
            },
        )

        if response.status_code != 200:
            raise AssertionError(f"查询接口状态码异常: {response.status_code}")

        print("应用启动阶段: 五个 Client Manager 已初始化")
        print("运行阶段: 查询路由可以访问")

    assert_not_initialized(
        lambda: qdrant_client_manager.client,
        "Qdrant Client",
    )
    assert_not_initialized(
        lambda: embedding_client_manager.client,
        "Embedding Client",
    )
    assert_not_initialized(
        lambda: es_client_manager.client,
        "Elasticsearch Client",
    )
    assert_not_initialized(
        lambda: meta_mysql_client_manager.engine,
        "Meta MySQL Engine",
    )
    assert_not_initialized(
        lambda: dw_mysql_client_manager.engine,
        "DW MySQL Engine",
    )

    print("应用关闭阶段: 五个 Client Manager 已释放")
    print("FastAPI lifespan 检查通过")


if __name__ == "__main__":
    main()
