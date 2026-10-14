"""Elasticsearch 客户端管理器。"""

from elasticsearch import AsyncElasticsearch

from app.conf.app_config import ESConfig, app_config


class ESClientManager:
    """管理 Elasticsearch 异步客户端的初始化与关闭"""

    def __init__(self, config: ESConfig):
        self.config = config
        self._client: AsyncElasticsearch | None = None

    def _get_url(self) -> str:
        """根据配置生成 Elasticsearch 服务地址。"""
        return f"http://{self.config.host}:{self.config.port}"

    # 把一个方法伪装成“属性”来访问
    @property
    def client(self) -> AsyncElasticsearch:
        """返回已初始化的客户端。"""
        if self._client is None:
            raise RuntimeError("Elasticsearch 客户端尚未初始化")
        return self._client

    def init(self) -> None:
        """初始化 Elasticsearch 异步客户端。"""
        if self._client is not None:
            raise RuntimeError("Elasticsearch 客户端已经初始化")

        self._client = AsyncElasticsearch(hosts=[self._get_url()])

    async def close(self) -> None:
        """关闭 Elasticsearch 异步客户端。"""
        client = self.client
        await client.close()
        self._client = None


es_client_manager = ESClientManager(app_config.es)
