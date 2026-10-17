"""表信息过滤节点。"""

import asyncio

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def filter_table(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> None:
    """输出表信息过滤节点的执行进度。"""

    writer = runtime.stream_writer
    writer("过滤表信息")

    await asyncio.sleep(0.5)
