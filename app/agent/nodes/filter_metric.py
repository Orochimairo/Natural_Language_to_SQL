"""指标信息过滤节点。"""

import asyncio

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState


async def filter_metric(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> None:
    """输出指标信息过滤节点的执行进度。"""

    writer = runtime.stream_writer
    writer("过滤指标信息")

    await asyncio.sleep(0.5)
