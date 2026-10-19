"""SQL 校正节点真实功能检查。"""

import asyncio
from copy import deepcopy
from typing import cast

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.correct_sql import correct_sql
from app.agent.nodes.validate_sql import validate_sql
from app.agent.state import DataAgentState
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
)
from app.repositories.mysql.dw.dw_mysql_repository import (
    DWMySQLRepository,
)


async def main() -> None:
    """制造真实 SQL 错误并检查模型校正结果。"""

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
            runtime = Runtime[DataAgentContext](
                context=context,
                stream_writer=print,
            )

            invalid_state = cast(
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
                    "sql": """
                        SELECT SUM(t1.order_amount) AS GMV
                        FROM fact_order t1
                        JOIN dim_region t2
                            ON t1.region_id = t2.region_id
                        WHERE t2.region_title = '华东'
                    """,
                    "error": None,
                },
            )

            validation_result = await validate_sql(
                invalid_state,
                runtime,
            )

            validation_error = validation_result["error"]

            if not validation_error:
                raise AssertionError("用于校正的错误 SQL 没有产生数据库错误")

            correction_state = cast(
                DataAgentState,
                {
                    **invalid_state,
                    **validation_result,
                },
            )
            original_correction_state = deepcopy(correction_state)

            correction_result = await correct_sql(
                correction_state,
                runtime,
            )

            corrected_sql = correction_result["sql"]

            if not isinstance(corrected_sql, str) or not corrected_sql:
                raise AssertionError("correct_sql 没有返回非空 SQL")

            if "```" in corrected_sql:
                raise AssertionError("校正后的 SQL 包含 Markdown 代码块")

            normalized_sql = corrected_sql.lstrip().upper()

            if not (
                normalized_sql.startswith("SELECT") or normalized_sql.startswith("WITH")
            ):
                raise AssertionError(f"校正结果不是查询 SQL: {corrected_sql}")

            if "region_title" in corrected_sql.lower():
                raise AssertionError("校正后的 SQL 仍然包含错误字段 region_title")

            required_identifiers = {
                "fact_order",
                "dim_region",
                "order_amount",
                "region_name",
            }
            missing_identifiers = {
                identifier
                for identifier in required_identifiers
                if identifier not in corrected_sql.lower()
            }

            if missing_identifiers:
                raise AssertionError(
                    f"校正后的 SQL 缺少必要表或字段: {sorted(missing_identifiers)}"
                )

            if correction_state != original_correction_state:
                raise AssertionError("correct_sql 修改了输入 State")

            await repository.validate(corrected_sql)

            print("原 SQL:")
            print(invalid_state["sql"].strip())
            print("数据库错误:")
            print(validation_error)
            print("校正后的 SQL:")
            print(corrected_sql)
            print("校正后的 SQL 已通过真实 MySQL EXPLAIN")
            print("输入 State 未被修改")
    finally:
        await dw_mysql_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
