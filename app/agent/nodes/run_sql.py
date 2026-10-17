"""SQL 执行节点。"""

import asyncio

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def run_sql(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> None:
    """输出 SQL 执行节点的执行进度。"""

    writer = runtime.stream_writer
    writer("执行SQL")

    await asyncio.sleep(0.5)
