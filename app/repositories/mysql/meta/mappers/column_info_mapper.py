"""字段元数据实体与 ORM 模型之间的转换器。"""

from dataclasses import asdict

from app.entities.column_info import ColumnInfo
from app.models.column_info import ColumnInfoMySQL


class ColumnInfoMapper:
    """负责 ColumnInfo 与 ColumnInfoMySQL 的双向转换。"""

    @staticmethod
    def to_model(entity: ColumnInfo) -> ColumnInfoMySQL:
        """将业务实体转换成 ORM 模型。"""

        return ColumnInfoMySQL(**asdict(entity))

    @staticmethod
    def to_entity(model: ColumnInfoMySQL) -> ColumnInfo:
        """将 ORM 模型转换成业务实体。"""

        return ColumnInfo(
            id=model.id,
            name=model.name,
            type=model.type,
            role=model.role,
            examples=model.examples,
            description=model.description,
            alias=model.alias,
            table_id=model.table_id,
        )