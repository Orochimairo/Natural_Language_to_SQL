"""SQL 生成节点真实 LLM 功能检查。"""

import asyncio
from copy import deepcopy
from typing import cast

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.generate_sql import generate_sql
from app.agent.state import DataAgentState


async def main() -> None:
    """使用真实 LLM 检查 SQL 生成节点。"""

    state = cast(
        DataAgentState,
        {
            "query": ("华东地区 iPhone 的销售总额是多少？"),
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
                            "name": "product_id",
                            "type": "varchar(64)",
                            "role": "foreign_key",
                            "examples": [],
                            "description": "商品外键",
                            "alias": ["商品ID"],
                        },
                        {
                            "name": "order_amount",
                            "type": "decimal(18,2)",
                            "role": "measure",
                            "examples": [
                                1999.0,
                                6999.0,
                            ],
                            "description": ("订单成交金额"),
                            "alias": [
                                "订单金额",
                                "成交金额",
                            ],
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
                            "description": ("地区唯一标识"),
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
                            "alias": [
                                "地区",
                                "区域",
                            ],
                        },
                    ],
                },
                {
                    "name": "dim_product",
                    "role": "dimension",
                    "description": "商品维度表",
                    "columns": [
                        {
                            "name": "product_id",
                            "type": "varchar(64)",
                            "role": "primary_key",
                            "examples": [],
                            "description": ("商品唯一标识"),
                            "alias": ["商品ID"],
                        },
                        {
                            "name": "product_name",
                            "type": "varchar(128)",
                            "role": "dimension",
                            "examples": [
                                "iPhone 15 Pro",
                                "Mate 60 Pro",
                            ],
                            "description": "商品名称",
                            "alias": [
                                "商品",
                                "产品名称",
                            ],
                        },
                    ],
                },
            ],
            "metric_infos": [
                {
                    "name": "GMV",
                    "description": ("所有订单成交金额的总和"),
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
            "error": None,
        },
    )

    original_state = deepcopy(state)
    events: list[dict[str, str]] = []

    runtime = Runtime[DataAgentContext](
        context=cast(DataAgentContext, {}),
        stream_writer=events.append,
    )

    result = await generate_sql(
        state,
        runtime,
    )

    expected_events = [
        {
            "type": "progress",
            "step": "生成SQL",
            "status": "running",
        },
        {
            "type": "progress",
            "step": "生成SQL",
            "status": "success",
        },
    ]

    if events != expected_events:
        raise AssertionError(f"SQL 生成事件不正确: {events}")

    sql = result["sql"]

    if not isinstance(sql, str) or not sql.strip():
        raise AssertionError("generate_sql 没有返回非空 SQL 字符串")

    if "```" in sql:
        raise AssertionError("生成的 SQL 包含 Markdown 代码块")

    normalized_sql = sql.lstrip().upper()

    if not (normalized_sql.startswith("SELECT") or normalized_sql.startswith("WITH")):
        raise AssertionError(f"生成结果不是查询 SQL: {sql}")

    sql_without_trailing_semicolon = sql.rstrip().removesuffix(";")

    if ";" in sql_without_trailing_semicolon:
        raise AssertionError("生成结果包含多条 SQL")

    required_identifiers = {
        "fact_order",
        "dim_region",
        "dim_product",
        "order_amount",
        "region_name",
        "product_name",
    }
    missing_identifiers = {
        identifier
        for identifier in required_identifiers
        if identifier not in sql.lower()
    }

    if missing_identifiers:
        raise AssertionError(
            f"生成的 SQL 缺少必要表或字段: {sorted(missing_identifiers)}"
        )

    if state != original_state:
        raise AssertionError("generate_sql 修改了输入 State")

    print("SQL 生成事件:", events)
    print("生成的 SQL:")
    print(sql)
    print("输入 State 未被修改")
    print("SQL 生成节点检查通过")


if __name__ == "__main__":
    asyncio.run(main())
