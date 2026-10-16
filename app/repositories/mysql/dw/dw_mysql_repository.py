"""数仓 MySQL 仓储。"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DWMySQLRepository:
    """负责读取 DW MySQL 中的真实结构和数据。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_column_types(self, table_name: str) -> dict[str, str]:
        """读取指定表的字段名称和真实数据库类型。"""

        sql = f"SHOW COLUMNS FROM {table_name}"
        result = await self.session.execute(text(sql))
        rows = result.mappings().fetchall()

        return {row["Field"]: row["Type"] for row in rows}

    async def get_column_values(
        self,
        table_name: str,
        column_name: str,
        limit: int = 10,
    ) -> list:
        """读取指定字段的去重值。"""

        sql = (
            f"SELECT DISTINCT {column_name} "
            f"FROM {table_name} "
            f"LIMIT {limit}"
        )
        result = await self.session.execute(text(sql))

        return [row[0] for row in result.fetchall()]