"""SQL 校正节点。"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

import yaml
from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def correct_sql(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> dict[str, str | None]:
    """根据数据库校验错误修正 SQL。"""

    step = "校正SQL"
    writer = runtime.stream_writer

    writer(
        {
            "type": "progress",
            "step": step,
            "status": "running",
        }
    )

    try:
        table_infos = state["table_infos"]
        metric_infos = state["metric_infos"]
        date_info = state["date_info"]
        db_info = state["db_info"]
        query = state["query"]
        sql = state["sql"]
        error = state["error"]

        if error is None:
            raise ValueError("没有 SQL 校验错误，不能执行 SQL 校正")

        prompt = PromptTemplate(
            template=load_prompt("correct_sql"),
            input_variables=[
                "table_infos",
                "metric_infos",
                "date_info",
                "db_info",
                "query",
                "sql",
                "error",
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
                "sql": sql,
                "error": error,
            }
        )

        corrected_sql = result.strip()

        if not corrected_sql:
            raise ValueError("模型校正后的 SQL 不能为空")

        logger.info(f"校正后的SQL: {corrected_sql}")

        writer(
            {
                "type": "progress",
                "step": step,
                "status": "success",
            }
        )

        return {
            "sql": corrected_sql,
            "error": None,
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
