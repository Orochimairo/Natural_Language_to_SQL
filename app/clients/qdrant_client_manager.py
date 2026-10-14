"""Qdrant 客户端管理器。"""

from qdrant_client import AsyncQdrantClient

from app.conf.app_config import QdrantConfig, app_config


class QdrantClientManager:
    """管理Qdrant异步客户端的初始化与关闭"""

    def __init__(self, config: QdrantConfig):
        self.config = config
        self._client: AsyncQdrantClient | None = None

    def _get_url(self) -> str:
        """根据配置生成 Qdrant 服务地址。"""
        return f"http://{self.config.host}:{self.config.port}"

    @property
    def client(self) -> AsyncQdrantClient:
        """返回已初始化的客户端。"""
        if self._client is None:
            raise RuntimeError("Qdrant 客户端尚未初始化")
        return self._client

    def init(self) -> None:
        """初始化 Qdrant 异步客户端。"""
        if self._client is not None:
            raise RuntimeError("Qdrant 客户端已经初始化")

        self._client = AsyncQdrantClient(url=self._get_url())

    async def close(self) -> None:
        """关闭 Qdrant 异步客户端。"""
        client = self.client
        await client.close()
        self._client = None


qdrant_client_manager = QdrantClientManager(app_config.qdrant)
