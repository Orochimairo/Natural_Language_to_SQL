"""SQL 校验节点真实数据库功能检查。"""

import asyncio
from copy import deepcopy
from typing import cast

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.validate_sql import validate_sql
from app.agent.state import DataAgentState
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
)
from app.repositories.mysql.dw.dw_mysql_repository import (
    DWMySQLRepository,
)


async def main() -> None:
    """使用真实 DW MySQL 检查 SQL 校验节点。"""

    dw_mysql_client_manager.init()

    try:
        async with dw_mysql_client_manager.session_factory() as session:
            repository = DWMySQLRepository(session)
            context = cast(
                DataAgentContext,
                {
                    "dw_mysql_repository": repository,
                },
            )

            valid_events: list[dict[str, str]] = []

            valid_runtime = Runtime[DataAgentContext](
                context=context,
                stream_writer=valid_events.append,
            )

            valid_state = cast(
                DataAgentState,
                {
                    "sql": """
                        SELECT SUM(order_amount) AS GMV
                        FROM fact_order
                    """,
                    "error": "旧错误",
                },
            )
            original_valid_state = deepcopy(valid_state)

            valid_result = await validate_sql(
                valid_state,
                valid_runtime,
            )

            expected_events = [
                {
                    "type": "progress",
                    "step": "校验SQL",
                    "status": "running",
                },
                {
                    "type": "progress",
                    "step": "校验SQL",
                    "status": "success",
                },
            ]

            if valid_events != expected_events:
                raise AssertionError(f"合法 SQL 事件不正确: {valid_events}")

            if valid_result != {"error": None}:
                raise AssertionError(f"合法 SQL 校验结果不正确: {valid_result}")

            if valid_state != original_valid_state:
                raise AssertionError("validate_sql 修改了合法 SQL 的输入 State")

            print(
                "合法 SQL 事件:",
                valid_events,
            )
            print(
                "合法 SQL 校验结果:",
                valid_result,
            )

            invalid_events: list[dict[str, str]] = []

            invalid_runtime = Runtime[DataAgentContext](
                context=context,
                stream_writer=invalid_events.append,
            )

            invalid_state = cast(
                DataAgentState,
                {
                    "sql": """
                        SELECT not_existing_column
                        FROM fact_order
                    """,
                    "error": None,
                },
            )
            original_invalid_state = deepcopy(invalid_state)

            invalid_result = await validate_sql(
                invalid_state,
                invalid_runtime,
            )

            if invalid_events != expected_events:
                raise AssertionError(f"非法 SQL 事件不正确: {invalid_events}")

            error_message = invalid_result["error"]

            if not isinstance(error_message, str) or not error_message:
                raise AssertionError("非法 SQL 没有返回数据库错误信息")

            if invalid_state != original_invalid_state:
                raise AssertionError("validate_sql 修改了非法 SQL 的输入 State")

            print(
                "非法 SQL 事件:",
                invalid_events,
            )
            print("非法 SQL 已转换为 State 错误")
            print(
                "错误类型:",
                type(error_message).__name__,
            )
            print("错误信息:", error_message)
            print("输入 State 未被修改")
            print("SQL 校验节点检查通过")
    finally:
        await dw_mysql_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
