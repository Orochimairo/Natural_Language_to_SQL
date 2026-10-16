"""字段指标关系实体与 ORM 模型之间的转换器。"""

from dataclasses import asdict

from app.entities.column_metric import ColumnMetric
from app.models.column_metric import ColumnMetricMySQL


class ColumnMetricMapper:
    """负责 ColumnMetric 与 ColumnMetricMySQL 的双向转换。"""

    @staticmethod
    def to_model(entity: ColumnMetric) -> ColumnMetricMySQL:
        """将业务实体转换成 ORM 模型。"""

        return ColumnMetricMySQL(**asdict(entity))

    @staticmethod
    def to_entity(model: ColumnMetricMySQL) -> ColumnMetric:
        """将 ORM 模型转换成业务实体。"""

        return ColumnMetric(
            column_id=model.column_id,
            metric_id=model.metric_id,
        )