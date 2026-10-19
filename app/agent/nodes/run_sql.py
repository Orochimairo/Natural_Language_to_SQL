"""SQL 执行节点。"""

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def run_sql(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> None:
    """执行最终 SQL 并将查询结果写入自定义流。"""

    step = "执行SQL"
    writer = runtime.stream_writer

    writer(
        {
            "type": "progress",
            "step": step,
            "status": "running",
        }
    )

    try:
        sql = state["sql"]
        dw_mysql_repository = runtime.context["dw_mysql_repository"]

        result = await dw_mysql_repository.run(sql)

        logger.info(f"SQL执行结果: {result}")

        writer(
            {
                "type": "progress",
                "step": step,
                "status": "success",
            }
        )

        writer(
            {
                "type": "result",
                "data": result,
            }
        )
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
