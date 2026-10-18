"""额外上下文补充节点。"""

from datetime import date

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import (
    DataAgentState,
    DateInfoState,
    DBInfoState,
)
from app.core.log import logger


async def add_extra_context(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> dict[str, DateInfoState | DBInfoState]:
    """补充当前日期和 DW 数据库环境信息。"""

    writer = runtime.stream_writer
    writer("添加额外上下文")

    today = date.today()

    date_info = DateInfoState(
        date=today.strftime("%Y-%m-%d"),
        weekday=today.strftime("%A"),
        quarter=f"Q{(today.month - 1) // 3 + 1}",
    )

    dw_mysql_repository = runtime.context["dw_mysql_repository"]
    database_info = await dw_mysql_repository.get_db_info()

    db_info = DBInfoState(
        dialect=database_info["dialect"],
        version=database_info["version"],
    )

    logger.info(f"日期信息: {date_info}")
    logger.info(f"数据库信息: {db_info}")

    return {
        "date_info": date_info,
        "db_info": db_info,
    }
