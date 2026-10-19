"""SQL 校验节点。"""

from langgraph.runtime import Runtime
from sqlalchemy.exc import SQLAlchemyError

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def validate_sql(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> dict[str, str | None]:
    """使用真实数据库校验 SQL，并返回校验错误。"""

    step = "校验SQL"
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

        try:
            await dw_mysql_repository.validate(sql)
        except SQLAlchemyError as error:
            error_message = str(error)

            logger.info(f"SQL语法错误: {error_message}")

            writer(
                {
                    "type": "progress",
                    "step": step,
                    "status": "success",
                }
            )

            return {
                "error": error_message,
            }

        logger.info("SQL语法正确")

        writer(
            {
                "type": "progress",
                "step": step,
                "status": "success",
            }
        )

        return {
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
