"""字段真实值召回节点。"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.value_info import ValueInfo
from app.prompt.prompt_loader import load_prompt


async def recall_value(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> dict[str, list[ValueInfo]]:
    """召回与用户问题相关的字段真实值。"""

    step = "召回字段取值"
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
        value_repository = runtime.context["value_es_repository"]

        prompt = PromptTemplate(
            template=load_prompt("extend_keywords_for_value_recall"),
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
            raise ValueError("字段值扩词结果必须是 JSON 数组")

        if not all(isinstance(keyword, str) for keyword in extended_keywords):
            raise ValueError("字段值扩词结果只能包含字符串")

        recall_keywords = list(
            dict.fromkeys(
                [
                    *keywords,
                    *extended_keywords,
                ]
            )
        )

        value_info_map: dict[str, ValueInfo] = {}

        for keyword in recall_keywords:
            value_infos = await value_repository.search(keyword)

            for value_info in value_infos:
                value_info_map.setdefault(
                    value_info.id,
                    value_info,
                )

        retrieved_value_infos = list(value_info_map.values())

        logger.info(f"字段值召回关键词: {recall_keywords}")
        logger.info(f"召回字段值: {list(value_info_map.keys())}")

        writer(
            {
                "type": "progress",
                "step": step,
                "status": "success",
            }
        )

        return {
            "retrieved_value_infos": (retrieved_value_infos),
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
