"""Embedding 客户端管理器。"""

from huggingface_hub import AsyncInferenceClient

from app.conf.app_config import EmbeddingConfig, app_config


class TEIEmbeddingClient:
    """为本地 TEI 提供项目需要的异步 Embedding 接口。"""

    def __init__(self, endpoint_url: str):
        self._client = AsyncInferenceClient(base_url=endpoint_url)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量生成文本向量。"""
        embeddings = await self._client.feature_extraction(text=texts)
        return embeddings.tolist()

    async def aembed_query(self, text: str) -> list[float]:
        """生成单条查询文本的向量。"""
        embeddings = await self.aembed_documents([text])
        return embeddings[0]

    async def close(self) -> None:
        """关闭底层异步 HTTP 客户端。"""
        await self._client.close()


class EmbeddingClientManager:
    """管理 Embedding 客户端的初始化与复用。"""

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self._client: TEIEmbeddingClient | None = None

    def _get_url(self) -> str:
        """根据配置生成 Embedding 服务地址。"""
        return f"http://{self.config.host}:{self.config.port}"

    @property
    def client(self) -> TEIEmbeddingClient:
        """返回已初始化的客户端。"""
        if self._client is None:
            raise RuntimeError("Embedding 客户端尚未初始化")
        return self._client

    def init(self) -> None:
        """初始化 Embedding 客户端。"""
        if self._client is not None:
            raise RuntimeError("Embedding 客户端已经初始化")

        self._client = TEIEmbeddingClient(endpoint_url=self._get_url())

    async def close(self) -> None:
        """关闭 Embedding 客户端。"""
        client = self.client
        await client.close()
        self._client = None


embedding_client_manager = EmbeddingClientManager(app_config.embedding)
