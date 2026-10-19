"""指标召回节点。"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.metric_info import MetricInfo
from app.prompt.prompt_loader import load_prompt


async def recall_metric(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> dict[str, list[MetricInfo]]:
    """召回与用户问题相关的业务指标。"""

    step = "召回指标信息"
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
        keywords = state["keywords"]

        embedding_client = runtime.context["embedding_client"]
        metric_repository = runtime.context["metric_qdrant_repository"]

        prompt = PromptTemplate(
            template=load_prompt("extend_keywords_for_metric_recall"),
            input_variables=["query"],
        )
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        extended_keywords = await chain.ainvoke(
            {
                "query": query,
            }
        )

        if not isinstance(extended_keywords, list):
            raise ValueError("指标扩词结果必须是 JSON 数组")

        if not all(isinstance(keyword, str) for keyword in extended_keywords):
            raise ValueError("指标扩词结果只能包含字符串")

        recall_keywords = list(
            dict.fromkeys(
                [
                    *keywords,
                    *extended_keywords,
                ]
            )
        )

        metric_info_map: dict[str, MetricInfo] = {}

        for keyword in recall_keywords:
            embedding = await embedding_client.aembed_query(keyword)
            metric_infos = await metric_repository.search(embedding)

            for metric_info in metric_infos:
                metric_info_map.setdefault(
                    metric_info.id,
                    metric_info,
                )

        retrieved_metric_infos = list(metric_info_map.values())

        logger.info(f"指标召回关键词: {recall_keywords}")
        logger.info(f"召回指标: {list(metric_info_map.keys())}")

        writer(
            {
                "type": "progress",
                "step": step,
                "status": "success",
            }
        )

        return {
            "retrieved_metric_infos": (retrieved_metric_infos),
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
