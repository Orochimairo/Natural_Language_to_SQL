"""额外上下文节点真实功能检查。"""

import asyncio
from copy import deepcopy
from datetime import date
from typing import cast

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.add_extra_context import (
    add_extra_context,
)
from app.agent.state import DataAgentState
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
)
from app.repositories.mysql.dw.dw_mysql_repository import (
    DWMySQLRepository,
)


async def main() -> None:
    """检查当前日期和真实 DW 数据库信息。"""

    dw_mysql_client_manager.init()

    try:
        async with dw_mysql_client_manager.session_factory() as session:
            state: DataAgentState = {
                "query": ("华东地区 iPhone 的销售总额是多少？"),
                "keywords": [
                    "华东地区",
                    "iPhone",
                    "销售总额",
                ],
                "retrieved_column_infos": [],
                "retrieved_metric_infos": [],
                "retrieved_value_infos": [],
                "table_infos": [],
                "metric_infos": [],
                "date_info": {
                    "date": "",
                    "weekday": "",
                    "quarter": "",
                },
                "db_info": {
                    "dialect": "",
                    "version": "",
                },
                "error": None,
            }

            original_state = deepcopy(state)

            context = cast(
                DataAgentContext,
                {
                    "dw_mysql_repository": (DWMySQLRepository(session)),
                },
            )
            runtime = Runtime[DataAgentContext](
                context=context,
                stream_writer=print,
            )

            result = await add_extra_context(
                state,
                runtime,
            )

            today = date.today()
            expected_date = today.strftime("%Y-%m-%d")
            expected_weekday = today.strftime("%A")
            expected_quarter = f"Q{(today.month - 1) // 3 + 1}"

            date_info = result["date_info"]
            db_info = result["db_info"]

            if date_info["date"] != expected_date:
                raise AssertionError(f"当前日期不正确: {date_info['date']}")

            if date_info["weekday"] != expected_weekday:
                raise AssertionError(f"当前星期不正确: {date_info['weekday']}")

            if date_info["quarter"] != expected_quarter:
                raise AssertionError(f"当前季度不正确: {date_info['quarter']}")

            if db_info["dialect"] != "mysql":
                raise AssertionError(f"数据库方言不正确: {db_info['dialect']}")

            if not db_info["version"]:
                raise AssertionError("数据库版本不能为空")

            if state != original_state:
                raise AssertionError("add_extra_context 修改了输入 State")

            print("日期信息:", date_info)
            print("数据库信息:", db_info)
            print("输入 State 未被修改")
    finally:
        await dw_mysql_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
