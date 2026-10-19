"""指标信息过滤节点。"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

import yaml
from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import (
    DataAgentState,
    MetricInfoState,
)
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def filter_metric(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> dict[str, list[MetricInfoState]]:
    """根据用户问题裁剪候选指标上下文。"""

    step = "过滤指标信息"
    writer = runtime.stream_writer

    writer(
        {
            "type": "progress",
            "step": step,
            "status": "running",
        }
    )

    try:
        query = state["query"]
        metric_infos: list[MetricInfoState] = state["metric_infos"]

        if not metric_infos:
            logger.info("没有候选指标需要过滤")

            writer(
                {
                    "type": "progress",
                    "step": step,
                    "status": "success",
                }
            )

            return {
                "metric_infos": [],
            }

        prompt = PromptTemplate(
            template=load_prompt("filter_metric_info"),
            input_variables=[
                "query",
                "metric_infos",
            ],
        )
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke(
            {
                "query": query,
                "metric_infos": yaml.dump(
                    metric_infos,
                    allow_unicode=True,
                    sort_keys=False,
                ),
            }
        )

        if not isinstance(result, list):
            raise ValueError("指标过滤结果必须是 JSON 数组")

        if not all(isinstance(metric_name, str) for metric_name in result):
            raise ValueError("指标过滤结果只能包含字符串")

        candidate_metric_names = {metric_info["name"] for metric_info in metric_infos}
        unknown_metric_names = set(result) - candidate_metric_names

        if unknown_metric_names:
            raise ValueError(
                f"指标过滤结果包含不存在的指标: {sorted(unknown_metric_names)}"
            )

        selected_metric_names = set(result)

        filtered_metric_infos = [
            MetricInfoState(
                name=metric_info["name"],
                description=(metric_info["description"]),
                relevant_columns=list(metric_info["relevant_columns"]),
                alias=list(metric_info["alias"]),
            )
            for metric_info in metric_infos
            if metric_info["name"] in selected_metric_names
        ]

        logger.info(
            "过滤后的指标信息: "
            f"{[metric_info['name'] for metric_info in filtered_metric_infos]}"
        )

        writer(
            {
                "type": "progress",
                "step": step,
                "status": "success",
            }
        )

        return {
            "metric_infos": filtered_metric_infos,
        }
    except Exception as error:
        logger.error(f"{step}失败: {error}")

        writer(
            {
                "type": "progress",
                "step": step,
                "status": "error",
            }
        )

        raise
