"""SQL 执行节点真实数据库功能检查。"""

import asyncio
from copy import deepcopy
from typing import cast

from langgraph.runtime import Runtime
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import DataAgentContext
from app.agent.nodes.run_sql import run_sql
from app.agent.state import DataAgentState
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
)
from app.repositories.mysql.dw.dw_mysql_repository import (
    DWMySQLRepository,
)


class RecordingDWMySQLRepository(DWMySQLRepository):
    """执行真实查询并记录结果，供检查脚本断言。"""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.last_result: list[dict] | None = None

    async def run(self, sql: str) -> list[dict]:
        """调用真实仓储实现并记录返回结果。"""

        result = await super().run(sql)
        self.last_result = result

        return result


async def main() -> None:
    """使用真实 DW MySQL 检查 SQL 执行节点。"""

    dw_mysql_client_manager.init()

    try:
        async with dw_mysql_client_manager.session_factory() as session:
            repository = RecordingDWMySQLRepository(session)

            context = cast(
                DataAgentContext,
                {
                    "dw_mysql_repository": repository,
                },
            )
            runtime = Runtime[DataAgentContext](
                context=context,
                stream_writer=print,
            )

            state = cast(
                DataAgentState,
                {
                    "sql": """
                        SELECT SUM(t1.order_amount) AS GMV
                        FROM fact_order t1
                        JOIN dim_region t2
                            ON t1.region_id = t2.region_id
                        WHERE t2.region_name = '华东'
                    """,
                    "error": None,
                },
            )
            original_state = deepcopy(state)

            node_result = await run_sql(
                state,
                runtime,
            )

            if node_result is not None:
                raise AssertionError(
                    f"run_sql 当前阶段不应返回 State 更新: {node_result}"
                )

            query_result = repository.last_result

            if not isinstance(query_result, list):
                raise AssertionError("run_sql 没有执行真实查询")

            if not query_result:
                raise AssertionError("SQL 查询结果为空")

            if not isinstance(query_result[0], dict):
                raise AssertionError("查询结果行不是 dict")

            if "GMV" not in query_result[0]:
                raise AssertionError(f"查询结果缺少 GMV 字段: {query_result[0]}")

            if state != original_state:
                raise AssertionError("run_sql 修改了输入 State")

            print("节点返回值:", node_result)
            print("真实查询结果:", query_result)
            print("输入 State 未被修改")
    finally:
        await dw_mysql_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
