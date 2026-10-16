"""元数据知识构建服务。"""
import uuid
from dataclasses import asdict
from pathlib import Path
from omegaconf import OmegaConf

from app.clients.embedding_client_manager import TEIEmbeddingClient
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import  MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.conf.meta_config import MetaConfig
from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.core.log import logger


class MetaKnowledgeService:
    """编排元数据知识构建流程。"""

    def __init__(
        self,
        meta_mysql_repository: MetaMySQLRepository,
        dw_mysql_repository: DWMySQLRepository,
        column_qdrant_repository: ColumnQdrantRepository,
        metric_qdrant_repository: MetricQdrantRepository,
        value_es_repository: ValueESRepository,
        embedding_client: TEIEmbeddingClient,
    ):
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = (
            column_qdrant_repository
        )
        self.metric_qdrant_repository = (
            metric_qdrant_repository
        )
        self.value_es_repository = value_es_repository
        self.embedding_client = embedding_client

    async def _save_tables_to_meta_db(
        self,
        meta_config: MetaConfig,
    ) -> list[ColumnInfo]:
        """补齐真实数仓信息并保存表和字段元数据。"""

        table_infos: list[TableInfo] = []
        column_infos: list[ColumnInfo] = []

        for table in meta_config.tables or []:
            table_infos.append(
                TableInfo(
                    id=table.name,
                    name=table.name,
                    role=table.role,
                    description=table.description,
                )
            )

            column_types = (
                await self.dw_mysql_repository.get_column_types(
                    table.name
                )
            )

            missing_columns = [
                column.name
                for column in table.columns
                if column.name not in column_types
            ]

            if missing_columns:
                missing_names = ", ".join(missing_columns)
                raise ValueError(
                    f"数仓表 {table.name} 缺少配置字段："
                    f"{missing_names}"
                )

            for column in table.columns:
                examples = (
                    await self.dw_mysql_repository.get_column_values(
                        table.name,
                        column.name,
                    )
                )

                column_infos.append(
                    ColumnInfo(
                        id=f"{table.name}.{column.name}",
                        name=column.name,
                        type=column_types[column.name],
                        role=column.role,
                        examples=examples,
                        description=column.description,
                        alias=column.alias,
                        table_id=table.name,
                    )
                )

        async with self.meta_mysql_repository.session.begin():
            self.meta_mysql_repository.save_table_infos(
                table_infos
            )
            self.meta_mysql_repository.save_column_infos(
                column_infos
            )

        return column_infos

    async def _save_column_infos_to_qdrant(
        self,
        column_infos: list[ColumnInfo],
    ) -> None:
        """将字段名称、说明和别名写入字段向量集合。"""

        await self.column_qdrant_repository.ensure_collection()

        ids: list[str] = []
        embedding_texts: list[str] = []
        payloads: list[dict] = []

        for column_info in column_infos:
            payload = asdict(column_info)
            texts = [
                column_info.name,
                column_info.description,
                *column_info.alias,
            ]

            for text in texts:
                ids.append(str(uuid.uuid4()))
                embedding_texts.append(text)
                payloads.append(payload)

        embeddings: list[list[float]] = []
        embedding_batch_size = 20

        for start in range(
            0,
            len(embedding_texts),
            embedding_batch_size,
        ):
            batch_texts = embedding_texts[
                start : start + embedding_batch_size
            ]
            batch_embeddings = (
                await self.embedding_client.aembed_documents(
                    batch_texts
                )
            )
            embeddings.extend(batch_embeddings)

        await self.column_qdrant_repository.upsert(
            ids,
            embeddings,
            payloads,
        )

    async def _save_value_infos_to_es(
        self,
        meta_config: MetaConfig,
        column_infos: list[ColumnInfo],
    ) -> None:
        """将允许同步的字段真实值写入 Elasticsearch。"""

        await self.value_es_repository.ensure_index()

        sync_column_ids = {
            f"{table.name}.{column.name}"
            for table in meta_config.tables or []
            for column in table.columns
            if column.sync
        }

        value_infos: list[ValueInfo] = []

        for column_info in column_infos:
            if column_info.id not in sync_column_ids:
                continue

            values = (
                await self.dw_mysql_repository.get_column_values(
                    column_info.table_id,
                    column_info.name,
                    limit=100000,
                )
            )

            for value in values:
                value_infos.append(
                    ValueInfo(
                        id=f"{column_info.id}.{value}",
                        value=value,
                        column_id=column_info.id,
                    )
                )

        await self.value_es_repository.index(value_infos)

    async def _save_metrics_to_meta_db(
        self,
        meta_config: MetaConfig,
    ) -> list[MetricInfo]:
        """保存指标及其依赖字段关系。"""

        metric_infos: list[MetricInfo] = []
        column_metrics: list[ColumnMetric] = []

        for metric in meta_config.metrics or []:
            metric_infos.append(
                MetricInfo(
                    id=metric.name,
                    name=metric.name,
                    description=metric.description,
                    relevant_columns=metric.relevant_columns,
                    alias=metric.alias,
                )
            )

            for column_id in metric.relevant_columns:
                column_metrics.append(
                    ColumnMetric(
                        column_id=column_id,
                        metric_id=metric.name,
                    )
                )

        async with self.meta_mysql_repository.session.begin():
            self.meta_mysql_repository.save_metric_infos(
                metric_infos
            )
            self.meta_mysql_repository.save_column_metrics(
                column_metrics
            )

        return metric_infos

    async def _save_metric_infos_to_qdrant(
        self,
        metric_infos: list[MetricInfo],
    ) -> None:
        """将指标名称、说明和别名写入指标向量集合。"""

        await self.metric_qdrant_repository.ensure_collection()

        ids: list[str] = []
        embedding_texts: list[str] = []
        payloads: list[dict] = []

        for metric_info in metric_infos:
            payload = asdict(metric_info)
            texts = [
                metric_info.name,
                metric_info.description,
                *metric_info.alias,
            ]

            for text in texts:
                ids.append(str(uuid.uuid4()))
                embedding_texts.append(text)
                payloads.append(payload)

        embeddings: list[list[float]] = []
        embedding_batch_size = 20

        for start in range(
            0,
            len(embedding_texts),
            embedding_batch_size,
        ):
            batch_texts = embedding_texts[
                start : start + embedding_batch_size
            ]
            batch_embeddings = (
                await self.embedding_client.aembed_documents(
                    batch_texts
                )
            )
            embeddings.extend(batch_embeddings)

        await self.metric_qdrant_repository.upsert(
            ids,
            embeddings,
            payloads,
        )

    async def build(
        self,
        config_path: Path,
    ) -> None:
        """根据配置构建完整的元数据知识库。"""

        context = OmegaConf.load(config_path)
        schema = OmegaConf.structured(MetaConfig)
        meta_config: MetaConfig = OmegaConf.to_object(
            OmegaConf.merge(schema, context)
        )

        if not meta_config.tables and not meta_config.metrics:
            raise ValueError(
                "元数据配置必须包含 tables 或 metrics"
            )

        if meta_config.tables:
            column_infos = (
                await self._save_tables_to_meta_db(
                    meta_config
                )
            )
            logger.info("表和字段元数据已保存到 Meta MySQL")

            await self._save_column_infos_to_qdrant(
                column_infos
            )
            logger.info("字段向量已写入 Qdrant")

            await self._save_value_infos_to_es(
                meta_config,
                column_infos,
            )
            logger.info("字段真实值已写入 Elasticsearch")

        if meta_config.metrics:
            metric_infos = (
                await self._save_metrics_to_meta_db(
                    meta_config
                )
            )
            logger.info(
                "指标和字段关系已保存到 Meta MySQL"
            )

            await self._save_metric_infos_to_qdrant(
                metric_infos
            )
            logger.info("指标向量已写入 Qdrant")