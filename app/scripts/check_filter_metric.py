"""指标过滤节点真实 LLM 功能检查。"""

import asyncio
from copy import deepcopy
from typing import cast

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.nodes.filter_metric import filter_metric
from app.agent.state import (
    DataAgentState,
    MetricInfoState,
)


async def main() -> None:
    """使用真实 LLM 检查候选指标过滤。"""

    metric_infos: list[MetricInfoState] = [
        MetricInfoState(
            name="GMV",
            description="所有订单成交金额的总和",
            relevant_columns=[
                "fact_order.order_amount",
            ],
            alias=[
                "成交总额",
                "销售总额",
            ],
        ),
        MetricInfoState(
            name="AOV",
            description="所有订单成交金额的平均值",
            relevant_columns=[
                "fact_order.order_amount",
            ],
            alias=[
                "客单价",
                "平均订单金额",
            ],
        ),
    ]

    original_metric_infos = deepcopy(metric_infos)

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
        "table_infos": [],
        "metric_infos": metric_infos,
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

    result = await filter_metric(
        state,
        runtime,
    )

    filtered_metric_infos = result["metric_infos"]
    filtered_metric_names = [
        metric_info["name"] for metric_info in filtered_metric_infos
    ]

    if filtered_metric_names != ["GMV"]:
        raise AssertionError(f"指标过滤结果不正确: {filtered_metric_names}")

    if metric_infos != original_metric_infos:
        raise AssertionError("filter_metric 修改了输入 metric_infos")

    print("过滤后的指标:", filtered_metric_names)
    print("输入 metric_infos 未被修改")


if __name__ == "__main__":
    asyncio.run(main())
