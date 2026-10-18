"""召回结果合并节点集成检查。"""

import asyncio
from dataclasses import replace
from typing import cast

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.merge_retrieved_info import merge_retrieved_info
from app.agent.state import DataAgentState
from app.clients.mysql_client_manager import meta_mysql_client_manager
from app.entities.metric_info import MetricInfo
from app.entities.value_info import ValueInfo
from app.repositories.mysql.meta.meta_mysql_repository import (
    MetaMySQLRepository,
)


async def main() -> None:
    """使用真实 Meta MySQL 检查召回结果合并。"""

    meta_mysql_client_manager.init()

    try:
        async with meta_mysql_client_manager.session_factory() as session:
            repository = MetaMySQLRepository(session)

            region_column = await repository.get_column_info_by_id(
                "dim_region.region_name"
            )
            product_column = await repository.get_column_info_by_id(
                "dim_product.product_name"
            )

            if region_column is None:
                raise LookupError("Meta MySQL 中不存在字段: dim_region.region_name")

            if product_column is None:
                raise LookupError("Meta MySQL 中不存在字段: dim_product.product_name")

            region_column = replace(
                region_column,
                examples=[
                    example for example in region_column.examples if example != "华东"
                ],
            )
            product_column = replace(
                product_column,
                examples=[
                    example
                    for example in product_column.examples
                    if example != "iPhone 15 Pro"
                ],
            )

            original_region_examples = list(region_column.examples)
            original_product_examples = list(product_column.examples)

            state: DataAgentState = {
                "query": "华东地区 iPhone 的销售总额是多少？",
                "keywords": [
                    "华东地区",
                    "iPhone",
                    "销售总额",
                ],
                "retrieved_column_infos": [
                    region_column,
                    product_column,
                ],
                "retrieved_metric_infos": [
                    MetricInfo(
                        id="GMV",
                        name="GMV",
                        description="所有订单成交金额的总和",
                        relevant_columns=[
                            "fact_order.order_amount",
                        ],
                        alias=[
                            "成交总额",
                            "销售总额",
                        ],
                    )
                ],
                "retrieved_value_infos": [
                    ValueInfo(
                        id="dim_region.region_name.华东",
                        value="华东",
                        column_id="dim_region.region_name",
                    ),
                    ValueInfo(
                        id=("dim_product.product_name.iPhone 15 Pro"),
                        value="iPhone 15 Pro",
                        column_id="dim_product.product_name",
                    ),
                ],
                "table_infos": [],
                "metric_infos": [],
                "error": None,
            }

            context = cast(
                DataAgentContext,
                {
                    "meta_mysql_repository": repository,
                },
            )

            runtime = Runtime[DataAgentContext](
                context=context,
                stream_writer=print,
            )

            result = await merge_retrieved_info(
                state,
                runtime,
            )

            table_infos = result["table_infos"]
            metric_infos = result["metric_infos"]

            table_info_map = {
                table_info["name"]: table_info for table_info in table_infos
            }

            expected_tables = {
                "dim_region",
                "dim_product",
                "fact_order",
            }

            if not expected_tables.issubset(table_info_map):
                raise AssertionError(
                    f"合并结果缺少预期表: {expected_tables - set(table_info_map)}"
                )

            column_name_map = {
                table_name: {
                    column_info["name"] for column_info in table_info["columns"]
                }
                for table_name, table_info in table_info_map.items()
            }

            expected_columns = {
                "dim_region": {
                    "region_name",
                    "region_id",
                },
                "dim_product": {
                    "product_name",
                    "product_id",
                },
                "fact_order": {
                    "order_amount",
                    "region_id",
                    "product_id",
                },
            }

            for table_name, column_names in expected_columns.items():
                missing_columns = column_names - column_name_map[table_name]

                if missing_columns:
                    raise AssertionError(f"{table_name} 缺少字段: {missing_columns}")

            region_name_info = next(
                column_info
                for column_info in table_info_map["dim_region"]["columns"]
                if column_info["name"] == "region_name"
            )
            product_name_info = next(
                column_info
                for column_info in table_info_map["dim_product"]["columns"]
                if column_info["name"] == "product_name"
            )

            if "华东" not in region_name_info["examples"]:
                raise AssertionError("华东没有写入 region_name.examples")

            if "iPhone 15 Pro" not in product_name_info["examples"]:
                raise AssertionError("iPhone 15 Pro 没有写入 product_name.examples")

            if region_column.examples != original_region_examples:
                raise AssertionError("节点修改了原始 region_name 召回对象")

            if product_column.examples != original_product_examples:
                raise AssertionError("节点修改了原始 product_name 召回对象")

            metric_names = [metric_info["name"] for metric_info in metric_infos]

            if metric_names != ["GMV"]:
                raise AssertionError(f"指标合并结果不正确: {metric_names}")

            print("表:", list(table_info_map))
            print("字段:", column_name_map)
            print("指标:", metric_names)
            print(
                "region_name examples:",
                region_name_info["examples"],
            )
            print(
                "product_name examples:",
                product_name_info["examples"],
            )
            print("原始召回对象未被修改")
    finally:
        await meta_mysql_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
