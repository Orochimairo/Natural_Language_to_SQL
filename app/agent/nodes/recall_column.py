"""字段召回节点。"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.prompt.prompt_loader import load_prompt


async def recall_column(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> dict[str, list[ColumnInfo]]:
    """召回与用户问题相关的字段元数据。"""

    writer = runtime.stream_writer
    writer("召回字段信息")

    query = state["query"]
    keywords = state["keywords"]

    embedding_client = runtime.context["embedding_client"]
    column_repository = runtime.context["column_qdrant_repository"]

    prompt = PromptTemplate(
        template=load_prompt("extend_keywords_for_column_recall"),
        input_variables=["query"],
    )
    output_parser = JsonOutputParser()
    chain = prompt | llm | output_parser

    extended_keywords = await chain.ainvoke({"query": query})

    if not isinstance(extended_keywords, list):
        raise ValueError("字段扩词结果必须是 JSON 数组")

    if not all(isinstance(keyword, str) for keyword in extended_keywords):
        raise ValueError("字段扩词结果只能包含字符串")

    recall_keywords = list(dict.fromkeys([*keywords, *extended_keywords]))

    column_info_map: dict[str, ColumnInfo] = {}

    for keyword in recall_keywords:
        embedding = await embedding_client.aembed_query(keyword)
        column_infos = await column_repository.search(embedding)

        for column_info in column_infos:
            column_info_map.setdefault(
                column_info.id,
                column_info,
            )

    retrieved_column_infos = list(column_info_map.values())

    logger.info(f"字段召回关键词: {recall_keywords}")
    logger.info(f"召回字段: {list(column_info_map.keys())}")

    return {"retrieved_column_infos": retrieved_column_infos}
