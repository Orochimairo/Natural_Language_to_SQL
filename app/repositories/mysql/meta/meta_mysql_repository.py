"""元数据库 MySQL 仓储。"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.entities.table_info import TableInfo
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper
from app.entities.column_info import ColumnInfo
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.entities.metric_info import MetricInfo
from app.repositories.mysql.meta.mappers.metric_info_mapper import MetricInfoMapper
from app.entities.column_metric import ColumnMetric
from app.repositories.mysql.meta.mappers.column_metric_mapper import ColumnMetricMapper
from app.models.table_info import TableInfoMySQL
from app.models.column_info import ColumnInfoMySQL


class MetaMySQLRepository:
    """负责读写 Meta MySQL 中的结构化元数据。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def save_table_infos(self, table_infos: list[TableInfo]) -> None:
        """将表元数据批量加入当前 Session。"""

        models = [
            TableInfoMapper.to_model(table_info)
            for table_info in table_infos
        ]
        self.session.add_all(models)

    def save_column_infos(self, column_infos: list[ColumnInfo]) -> None:
        """将字段元数据批量加入当前 Session。"""

        models = [
            ColumnInfoMapper.to_model(column_info)
            for column_info in column_infos
        ]
        self.session.add_all(models)

    def save_metric_infos(self, metric_infos: list[MetricInfo]) -> None:
        """将指标元数据批量加入当前 Session。"""

        models = [
            MetricInfoMapper.to_model(metric_info)
            for metric_info in metric_infos
        ]
        self.session.add_all(models)

    def save_column_metrics(
        self,
        column_metrics: list[ColumnMetric],
    ) -> None:
        """将字段与指标的关联关系批量加入当前 Session。"""

        models = [
            ColumnMetricMapper.to_model(column_metric)
            for column_metric in column_metrics
        ]
        self.session.add_all(models)

    async def get_table_info_by_id(
        self,
        id: str,
    ) -> TableInfo | None:
        """根据表编号读取表元数据。"""

        model = await self.session.get(TableInfoMySQL, id)

        if model is None:
            return None

        return TableInfoMapper.to_entity(model)

    async def get_column_info_by_id(
        self,
        id: str,
    ) -> ColumnInfo | None:
        """根据字段编号读取字段元数据。"""

        model = await self.session.get(ColumnInfoMySQL, id)

        if model is None:
            return None

        return ColumnInfoMapper.to_entity(model)

    async def get_key_columns_by_table_id(
        self,
        table_id: str,
    ) -> list[ColumnInfo]:
        """读取指定表的主键和外键字段。"""

        statement = select(ColumnInfoMySQL).where(
            ColumnInfoMySQL.table_id == table_id,
            ColumnInfoMySQL.role.in_(
                ("primary_key", "foreign_key"),
            ),
        )

        result = await self.session.scalars(statement)

        return [
            ColumnInfoMapper.to_entity(model)
            for model in result.all()
        ]