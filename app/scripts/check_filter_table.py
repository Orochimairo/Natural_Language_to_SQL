"""表信息过滤节点真实 LLM 功能检查。"""

import asyncio
from copy import deepcopy
from typing import Any, cast

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.filter_table import filter_table
from app.agent.state import (
    ColumnInfoState,
    DataAgentState,
    TableInfoState,
)


def make_column(
    name: str,
    type_: str,
    role: str,
    description: str,
    examples: list[Any] | None = None,
    alias: list[str] | None = None,
) -> ColumnInfoState:
    """构造检查所需的字段上下文。"""

    return ColumnInfoState(
        name=name,
        type=type_,
        role=role,
        examples=examples or [],
        description=description,
        alias=alias or [],
    )


async def main() -> None:
    """使用真实 LLM 检查表和字段过滤。"""

    table_infos: list[TableInfoState] = [
        TableInfoState(
            name="dim_region",
            role="dimension",
            description="地区维度表",
            columns=[
                make_column(
                    name="region_id",
                    type_="varchar(64)",
                    role="primary_key",
                    description="地区唯一标识",
                    alias=["地区ID"],
                ),
                make_column(
                    name="region_name",
                    type_="varchar(64)",
                    role="dimension",
                    description="地区名称",
                    examples=["华北", "华南", "华东"],
                    alias=["地区", "区域"],
                ),
            ],
        ),
        TableInfoState(
            name="dim_product",
            role="dimension",
            description="商品维度表",
            columns=[
                make_column(
                    name="product_id",
                    type_="varchar(64)",
                    role="primary_key",
                    description="商品唯一标识",
                    alias=["商品ID"],
                ),
                make_column(
                    name="product_name",
                    type_="varchar(128)",
                    role="dimension",
                    description="商品名称",
                    examples=[
                        "iPhone 15 Pro",
                        "Mate 60 Pro",
                    ],
                    alias=["商品", "产品名称"],
                ),
            ],
        ),
        TableInfoState(
            name="fact_order",
            role="fact",
            description="订单事实表",
            columns=[
                make_column(
                    name="order_id",
                    type_="varchar(64)",
                    role="primary_key",
                    description="订单唯一标识",
                    alias=["订单ID"],
                ),
                make_column(
                    name="region_id",
                    type_="varchar(64)",
                    role="foreign_key",
                    description="地区外键",
                    alias=["地区ID"],
                ),
                make_column(
                    name="product_id",
                    type_="varchar(64)",
                    role="foreign_key",
                    description="商品外键",
                    alias=["商品ID"],
                ),
                make_column(
                    name="customer_id",
                    type_="varchar(64)",
                    role="foreign_key",
                    description="客户外键",
                    alias=["客户ID"],
                ),
                make_column(
                    name="date_id",
                    type_="int",
                    role="foreign_key",
                    description="日期外键",
                    alias=["日期ID"],
                ),
                make_column(
                    name="order_amount",
                    type_="decimal(18,2)",
                    role="measure",
                    description="订单成交金额",
                    examples=[1999.00, 6999.00],
                    alias=["订单金额", "成交金额"],
                ),
            ],
        ),
    ]

    original_table_infos = deepcopy(table_infos)

    state: DataAgentState = {
        "query": "华东地区 iPhone 的销售总额是多少？",
        "keywords": [
            "华东地区",
            "iPhone",
            "销售总额",
        ],
        "retrieved_column_infos": [],
        "retrieved_metric_infos": [],
        "retrieved_value_infos": [],
        "table_infos": table_infos,
        "metric_infos": [],
        "error": None,
    }

    context = cast(
        DataAgentContext,
        {},
    )
    runtime = Runtime[DataAgentContext](
        context=context,
        stream_writer=print,
    )

    result = await filter_table(
        state,
        runtime,
    )

    filtered_table_infos = result["table_infos"]
    filtered_table_map = {
        table_info["name"]: table_info for table_info in filtered_table_infos
    }

    expected_tables = {
        "dim_region",
        "dim_product",
        "fact_order",
    }

    if set(filtered_table_map) != expected_tables:
        raise AssertionError(f"表过滤结果不正确: {set(filtered_table_map)}")

    filtered_column_names = {
        table_name: {column_info["name"] for column_info in table_info["columns"]}
        for table_name, table_info in filtered_table_map.items()
    }

    required_columns = {
        "dim_region": {
            "region_id",
            "region_name",
        },
        "dim_product": {
            "product_id",
            "product_name",
        },
        "fact_order": {
            "region_id",
            "product_id",
            "order_amount",
        },
    }

    for table_name, column_names in required_columns.items():
        missing_columns = column_names - filtered_column_names[table_name]

        if missing_columns:
            raise AssertionError(f"{table_name} 缺少必要字段: {missing_columns}")

    unnecessary_fact_columns = {
        "order_id",
        "customer_id",
        "date_id",
    }
    retained_unnecessary_columns = (
        unnecessary_fact_columns & filtered_column_names["fact_order"]
    )

    if retained_unnecessary_columns:
        raise AssertionError(
            f"fact_order 保留了无关字段: {retained_unnecessary_columns}"
        )

    if table_infos != original_table_infos:
        raise AssertionError("filter_table 修改了输入 table_infos")

    print("过滤后的表:", list(filtered_table_map))
    print("过滤后的字段:", filtered_column_names)
    print("输入 table_infos 未被修改")


if __name__ == "__main__":
    asyncio.run(main())
