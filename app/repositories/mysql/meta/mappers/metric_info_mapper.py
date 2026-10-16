"""指标元数据实体与 ORM 模型之间的转换器。"""

from dataclasses import asdict

from app.entities.metric_info import MetricInfo
from app.models.metric_info import MetricInfoMySQL


class MetricInfoMapper:
    """负责 MetricInfo 与 MetricInfoMySQL 的双向转换。"""

    @staticmethod
    def to_model(entity: MetricInfo) -> MetricInfoMySQL:
        """将业务实体转换成 ORM 模型。"""

        return MetricInfoMySQL(**asdict(entity))

    @staticmethod
    def to_entity(model: MetricInfoMySQL) -> MetricInfo:
        """将 ORM 模型转换成业务实体。"""

        return MetricInfo(
            id=model.id,
            name=model.name,
            description=model.description,
            relevant_columns=model.relevant_columns,
            alias=model.alias,
        )