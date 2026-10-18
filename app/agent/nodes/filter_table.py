"""表信息过滤节点。"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

import yaml
from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState, TableInfoState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def filter_table(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> dict[str, list[TableInfoState]]:
    """根据用户问题裁剪候选表和字段上下文。"""

    writer = runtime.stream_writer
    writer("过滤表信息")

    query = state["query"]
    table_infos: list[TableInfoState] = state["table_infos"]

    prompt = PromptTemplate(
        template=load_prompt("filter_table_info"),
        input_variables=[
            "query",
            "table_infos",
        ],
    )
    output_parser = JsonOutputParser()
    chain = prompt | llm | output_parser

    result = await chain.ainvoke(
        {
            "query": query,
            "table_infos": yaml.dump(
                table_infos,
                allow_unicode=True,
                sort_keys=False,
            ),
        }
    )

    if not isinstance(result, dict):
        raise ValueError("表过滤结果必须是 JSON 对象")

    if not result:
        raise ValueError("表过滤结果不能为空")

    candidate_table_map = {table_info["name"]: table_info for table_info in table_infos}

    unknown_table_names = set(result) - set(candidate_table_map)

    if unknown_table_names:
        raise ValueError(f"表过滤结果包含不存在的表: {sorted(unknown_table_names)}")

    for table_name, column_names in result.items():
        if not isinstance(column_names, list):
            raise ValueError(f"表 {table_name} 的字段选择结果必须是数组")

        if not column_names:
            raise ValueError(f"表 {table_name} 至少需要选择一个字段")

        if not all(isinstance(column_name, str) for column_name in column_names):
            raise ValueError(f"表 {table_name} 的字段名称必须都是字符串")

        candidate_column_names = {
            column_info["name"]
            for column_info in candidate_table_map[table_name]["columns"]
        }
        unknown_column_names = set(column_names) - candidate_column_names

        if unknown_column_names:
            raise ValueError(
                f"表 {table_name} 包含不存在的字段: {sorted(unknown_column_names)}"
            )

    filtered_table_infos: list[TableInfoState] = []

    for table_info in table_infos:
        table_name = table_info["name"]

        if table_name not in result:
            continue

        selected_column_names = set(result[table_name])

        filtered_columns = [
            column_info.copy()
            for column_info in table_info["columns"]
            if column_info["name"] in selected_column_names
        ]

        filtered_table_infos.append(
            TableInfoState(
                name=table_info["name"],
                role=table_info["role"],
                description=table_info["description"],
                columns=filtered_columns,
            )
        )

    logger.info(
        f"过滤后的表信息: {[table_info['name'] for table_info in filtered_table_infos]}"
    )

    return {"table_infos": filtered_table_infos}
