"""字段值 Elasticsearch 仓储。"""

from elasticsearch import AsyncElasticsearch
from dataclasses import asdict

from app.entities.value_info import ValueInfo
from app.conf.app_config import app_config


class ValueESRepository:
    """负责字段值索引的创建、写入和检索。"""

    index_name = app_config.es.index_name

    index_mappings = {
        "dynamic": False,
        "properties": {
            "id": {
                "type": "keyword",
            },
            "value": {
                "type": "text",
                "analyzer": "ik_max_word",
                "search_analyzer": "ik_max_word",
            },
            "column_id": {
                "type": "keyword",
            },
        },
    }

    def __init__(self, client: AsyncElasticsearch):
        self.client = client

    async def ensure_index(self) -> None:
        """确保字段值索引存在。"""

        exists = await self.client.indices.exists(
            index=self.index_name
        )

        if not exists:
            await self.client.indices.create(
                index=self.index_name,
                mappings=self.index_mappings,
            )

    async def index(
        self,
        value_infos: list[ValueInfo],
        batch_size: int = 20,
    ) -> None:
        """分批写入字段值文档。"""

        if batch_size <= 0:
            raise ValueError("batch_size 必须大于 0")

        if not value_infos:
            return

        for start in range(0, len(value_infos), batch_size):
            batch = value_infos[start : start + batch_size]
            operations: list[dict] = []

            for value_info in batch:
                operations.append(
                    {
                        "index": {
                            "_index": self.index_name,
                            "_id": value_info.id,
                        }
                    }
                )
                operations.append(asdict(value_info))

            response = await self.client.bulk(
                operations=operations
            )

            if response["errors"]:
                failed_items = [
                    item["index"]
                    for item in response["items"]
                    if "error" in item["index"]
                ]
                raise RuntimeError(
                    f"Elasticsearch 批量写入失败：{failed_items}"
                )
            
    async def search(
        self,
        keyword: str,
        score_threshold: float = 0.6,
        limit: int = 20,
    ) -> list[ValueInfo]:
        """根据关键词检索字段值。"""

        if not keyword.strip():
            raise ValueError("keyword 不能为空")

        if score_threshold < 0:
            raise ValueError("score_threshold 不能小于 0")

        if limit <= 0:
            raise ValueError("limit 必须大于 0")

        response = await self.client.search(
            index=self.index_name,
            query={
                "match": {
                    "value": keyword,
                }
            },
            min_score=score_threshold,
            size=limit,
        )

        value_infos: list[ValueInfo] = []

        for hit in response["hits"]["hits"]:
            source = hit.get("_source")

            if source is None:
                raise ValueError(
                    "Elasticsearch 命中文档缺少 _source"
                )

            value_infos.append(ValueInfo(**source))

        return value_infos