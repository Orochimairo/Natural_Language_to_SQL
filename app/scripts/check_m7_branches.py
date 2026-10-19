"""M7 SQL 条件分支功能检查。"""

import asyncio
from typing import cast

from langgraph.constants import END, START
from langgraph.graph import StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import DataAgentContext
from app.agent.nodes.correct_sql import correct_sql
from app.agent.nodes.run_sql import run_sql
from app.agent.nodes.validate_sql import validate_sql
from app.agent.state import DataAgentState
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
)
from app.repositories.mysql.dw.dw_mysql_repository import (
    DWMySQLRepository,
)


class RecordingDWMySQLRepository(DWMySQLRepository):
    """执行真实查询并记录 SQL 和结果。"""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.executed_sqls: list[str] = []
        self.results: list[list[dict]] = []

    async def run(self, sql: str) -> list[dict]:
        """调用真实查询并记录调用信息。"""

        result = await super().run(sql)

        self.executed_sqls.append(sql)
        self.results.append(result)

        return result


def build_m7_branch_graph():
    """构造只包含 M7 条件分支的检查图。"""

    graph_builder = StateGraph(
        state_schema=DataAgentState,
        context_schema=DataAgentContext,
    )

    graph_builder.add_node(
        "validate_sql",
        validate_sql,
    )
    graph_builder.add_node(
        "correct_sql",
        correct_sql,
    )
    graph_builder.add_node(
        "run_sql",
        run_sql,
    )

    graph_builder.add_edge(
        START,
        "validate_sql",
    )
    graph_builder.add_conditional_edges(
        source="validate_sql",
        path=lambda state: "run_sql" if state["error"] is None else "correct_sql",
        path_map={
            "run_sql": "run_sql",
            "correct_sql": "correct_sql",
        },
    )
    graph_builder.add_edge(
        "correct_sql",
        "run_sql",
    )
    graph_builder.add_edge(
        "run_sql",
        END,
    )

    return graph_builder.compile()


def make_state(sql: str) -> DataAgentState:
    """构造分支检查所需的 SQL 上下文。"""

    return cast(
        DataAgentState,
        {
            "query": "华东地区的销售总额是多少？",
            "table_infos": [
                {
                    "name": "fact_order",
                    "role": "fact",
                    "description": "订单事实表",
                    "columns": [
                        {
                            "name": "region_id",
                            "type": "varchar(64)",
                            "role": "foreign_key",
                            "examples": [],
                            "description": "地区外键",
                            "alias": ["地区ID"],
                        },
                        {
                            "name": "order_amount",
                            "type": "decimal(18,2)",
                            "role": "measure",
                            "examples": [1999.0, 6999.0],
                            "description": "订单成交金额",
                            "alias": ["订单金额", "成交金额"],
                        },
                    ],
                },
                {
                    "name": "dim_region",
                    "role": "dimension",
                    "description": "地区维度表",
                    "columns": [
                        {
                            "name": "region_id",
                            "type": "varchar(64)",
                            "role": "primary_key",
                            "examples": [],
                            "description": "地区唯一标识",
                            "alias": ["地区ID"],
                        },
                        {
                            "name": "region_name",
                            "type": "varchar(64)",
                            "role": "dimension",
                            "examples": [
                                "华北",
                                "华南",
                                "华东",
                            ],
                            "description": "地区名称",
                            "alias": ["地区", "区域"],
                        },
                    ],
                },
            ],
            "metric_infos": [
                {
                    "name": "GMV",
                    "description": "所有订单成交金额的总和",
                    "relevant_columns": [
                        "fact_order.order_amount",
                    ],
                    "alias": [
                        "销售总额",
                        "成交额",
                    ],
                }
            ],
            "date_info": {
                "date": "2026-10-19",
                "weekday": "Monday",
                "quarter": "Q4",
            },
            "db_info": {
                "dialect": "mysql",
                "version": "8.0.46",
            },
            "sql": sql,
            "error": None,
        },
    )


async def collect_events(
    graph,
    state: DataAgentState,
    context: DataAgentContext,
) -> list[str]:
    """执行检查图并收集节点进度。"""

    events: list[str] = []

    async for event in graph.astream(
        input=state,
        context=context,
        stream_mode="custom",
    ):
        events.append(event)

    return events


async def main() -> None:
    """验证校验成功和校验失败两条分支。"""

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
            graph = build_m7_branch_graph()

            valid_sql = """
                SELECT SUM(t1.order_amount) AS GMV
                FROM fact_order t1
                JOIN dim_region t2
                    ON t1.region_id = t2.region_id
                WHERE t2.region_name = '华东'
            """
            valid_state = make_state(valid_sql)

            valid_events = await collect_events(
                graph,
                valid_state,
                context,
            )

            if valid_events != [
                "校验SQL",
                "执行SQL",
            ]:
                raise AssertionError(f"合法 SQL 的分支不正确: {valid_events}")

            if len(repository.executed_sqls) != 1:
                raise AssertionError("合法 SQL 没有且仅执行一次")

            if repository.executed_sqls[0].strip() != valid_sql.strip():
                raise AssertionError("合法 SQL 在执行前被意外修改")

            if not repository.results[0]:
                raise AssertionError("合法 SQL 查询结果为空")

            if "GMV" not in repository.results[0][0]:
                raise AssertionError(f"合法 SQL 结果缺少 GMV: {repository.results[0]}")

            print("合法 SQL 分支:", valid_events)
            print("合法 SQL 结果:", repository.results[0])

            invalid_sql = """
                SELECT SUM(t1.order_amount) AS GMV
                FROM fact_order t1
                JOIN dim_region t2
                    ON t1.region_id = t2.region_id
                WHERE t2.region_title = '华东'
            """
            invalid_state = make_state(invalid_sql)

            invalid_events = await collect_events(
                graph,
                invalid_state,
                context,
            )

            if invalid_events != [
                "校验SQL",
                "校正SQL",
                "执行SQL",
            ]:
                raise AssertionError(f"非法 SQL 的分支不正确: {invalid_events}")

            if len(repository.executed_sqls) != 2:
                raise AssertionError("校正后的 SQL 没有且仅执行一次")

            corrected_sql = repository.executed_sqls[1]

            if "region_title" in corrected_sql.lower():
                raise AssertionError("最终执行的 SQL 仍然包含错误字段")

            if "region_name" not in corrected_sql.lower():
                raise AssertionError("最终执行的 SQL 没有使用正确字段")

            if not repository.results[1]:
                raise AssertionError("校正后的 SQL 查询结果为空")

            if "GMV" not in repository.results[1][0]:
                raise AssertionError(
                    f"校正后的 SQL 结果缺少 GMV: {repository.results[1]}"
                )

            print("非法 SQL 分支:", invalid_events)
            print("最终执行的修正 SQL:")
            print(corrected_sql)
            print("校正分支结果:", repository.results[1])
            print("M7 两条条件分支检查通过")
    finally:
        await dw_mysql_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
