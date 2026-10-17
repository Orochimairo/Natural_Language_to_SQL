"""SQL 校正节点。"""

import asyncio

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def correct_sql(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> None:
    """输出 SQL 校正节点的执行进度。"""

    writer = runtime.stream_writer
    writer("校正SQL")

    await asyncio.sleep(0.5)
