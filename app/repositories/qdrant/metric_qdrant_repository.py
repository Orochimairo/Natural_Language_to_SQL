"""指标向量 Qdrant 仓储。"""

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.conf.app_config import app_config
from app.entities.metric_info import MetricInfo


class MetricQdrantRepository:
    """负责指标向量集合的创建、写入和检索。"""

    collection_name = "metric_info_collection"

    def __init__(self, client: AsyncQdrantClient):
        self.client = client

    async def ensure_collection(self) -> None:
        """确保指标向量集合存在。"""

        exists = await self.client.collection_exists(
            self.collection_name
        )

        if not exists:
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=app_config.qdrant.embedding_size,
                    distance=Distance.COSINE,
                ),
            )

    async def upsert(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        payloads: list[dict],
        batch_size: int = 10,
    ) -> None:
        """分批写入指标向量 point。"""

        if not (
            len(ids) == len(embeddings) == len(payloads)
        ):
            raise ValueError(
                "ids、embeddings 和 payloads 的数量必须一致"
            )

        if batch_size <= 0:
            raise ValueError("batch_size 必须大于 0")

        points = [
            PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload,
            )
            for point_id, embedding, payload in zip(
                ids,
                embeddings,
                payloads,
            )
        ]

        for start in range(0, len(points), batch_size):
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points[start : start + batch_size],
            )

    async def search(
        self,
        embedding: list[float],
        score_threshold: float = 0.6,
        limit: int = 20,
    ) -> list[MetricInfo]:
        """根据向量相似度检索指标元数据。"""

        if limit <= 0:
            raise ValueError("limit 必须大于 0")

        result = await self.client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            score_threshold=score_threshold,
            limit=limit,
        )

        metric_infos: list[MetricInfo] = []

        for point in result.points:
            if point.payload is None:
                raise ValueError("指标向量 point 缺少 payload")

            metric_infos.append(
                MetricInfo(**point.payload)
            )

        return metric_infos