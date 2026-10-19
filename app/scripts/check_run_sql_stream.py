"""SQL 执行节点自定义流功能检查。"""

import asyncio
from copy import deepcopy
from typing import cast

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.run_sql import run_sql
from app.agent.state import DataAgentState
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
)
from app.repositories.mysql.dw.dw_mysql_repository import (
    DWMySQLRepository,
)


async def main() -> None:
    """检查真实查询结果能够进入自定义流。"""

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

            events: list[object] = []

            runtime = Runtime[DataAgentContext](
                context=context,
                stream_writer=events.append,
            )

            state = cast(
                DataAgentState,
                {
                    "sql": """
                        SELECT SUM(order_amount) AS GMV
                        FROM fact_order
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
                raise AssertionError(f"run_sql 不应返回 State 更新: {node_result}")

            if len(events) != 3:
                raise AssertionError(f"run_sql 流事件数量不正确: {events}")

            expected_progress_events = [
                {
                    "type": "progress",
                    "step": "执行SQL",
                    "status": "running",
                },
                {
                    "type": "progress",
                    "step": "执行SQL",
                    "status": "success",
                },
            ]

            if events[:2] != expected_progress_events:
                raise AssertionError(f"SQL 执行进度事件不正确: {events[:2]}")

            result_event = events[2]

            if not isinstance(result_event, dict):
                raise AssertionError(f"结果事件不是字典: {result_event}")

            if result_event.get("type") != "result":
                raise AssertionError(f"结果事件类型不正确: {result_event}")

            result_data = result_event.get("data")

            if not isinstance(result_data, list) or not result_data:
                raise AssertionError(f"结果事件没有查询数据: {result_event}")

            if not isinstance(result_data[0], dict):
                raise AssertionError(f"查询结果行不是字典: {result_data[0]}")

            if "GMV" not in result_data[0]:
                raise AssertionError(f"查询结果缺少 GMV: {result_data}")

            if state != original_state:
                raise AssertionError("run_sql 修改了输入 State")

            print("流事件:", events)
            print("节点返回值:", node_result)
            print("输入 State 未被修改")
            print("SQL 结果流检查通过")
    finally:
        await dw_mysql_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
