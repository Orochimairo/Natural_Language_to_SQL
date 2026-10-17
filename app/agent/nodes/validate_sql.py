"""SQL 校验节点。"""

import asyncio

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def validate_sql(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> dict[str, str | None]:
    """输出 SQL 校验进度并返回临时校验结果。"""

    writer = runtime.stream_writer
    writer("校验SQL")

    await asyncio.sleep(0.5)

    return {"error": None}
