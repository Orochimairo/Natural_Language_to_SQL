"""表元数据实体与 ORM 模型之间的转换器。"""

from dataclasses import asdict

from app.entities.table_info import TableInfo
from app.models.table_info import TableInfoMySQL


class TableInfoMapper:
    """负责 TableInfo 与 TableInfoMySQL 的双向转换。"""

    @staticmethod
    def to_model(entity: TableInfo) -> TableInfoMySQL:
        """将业务实体转换成 ORM 模型。"""

        return TableInfoMySQL(**asdict(entity))

    @staticmethod
    def to_entity(model: TableInfoMySQL) -> TableInfo:
        """将 ORM 模型转换成业务实体。"""

        return TableInfo(
            id=model.id,
            name=model.name,
            role=model.role,
            description=model.description,
        )