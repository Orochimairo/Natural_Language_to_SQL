"""SQL 生成节点。"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

import yaml
from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def generate_sql(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> dict[str, str]:
    """根据用户问题和上下文生成候选 SQL。"""

    writer = runtime.stream_writer
    writer("生成SQL")

    table_infos = state["table_infos"]
    metric_infos = state["metric_infos"]
    date_info = state["date_info"]
    db_info = state["db_info"]
    query = state["query"]

    prompt = PromptTemplate(
        template=load_prompt("generate_sql"),
        input_variables=[
            "table_infos",
            "metric_infos",
            "date_info",
            "db_info",
            "query",
        ],
    )
    output_parser = StrOutputParser()
    chain = prompt | llm | output_parser

    result = await chain.ainvoke(
        {
            "table_infos": yaml.dump(
                table_infos,
                allow_unicode=True,
                sort_keys=False,
            ),
            "metric_infos": yaml.dump(
                metric_infos,
                allow_unicode=True,
                sort_keys=False,
            ),
            "date_info": yaml.dump(
                date_info,
                allow_unicode=True,
                sort_keys=False,
            ),
            "db_info": yaml.dump(
                db_info,
                allow_unicode=True,
                sort_keys=False,
            ),
            "query": query,
        }
    )

    sql = result.strip()

    if not sql:
        raise ValueError("模型生成的 SQL 不能为空")

    logger.info(f"生成的SQL: {sql}")

    return {"sql": sql}
