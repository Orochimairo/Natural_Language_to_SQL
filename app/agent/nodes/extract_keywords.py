"""关键词抽取节点。"""

import jieba.analyse
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def extract_keywords(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext],
) -> dict[str, list[str]]:
    """从用户问题中提取用于多路召回的关键词。"""

    writer = runtime.stream_writer
    writer("抽取关键词")

    query = state["query"]

    if not query.strip():
        raise ValueError("query 不能为空")

    allow_pos = (
        "n",
        "nr",
        "ns",
        "nt",
        "nz",
        "v",
        "vn",
        "a",
        "an",
        "eng",
        "i",
        "l",
    )

    keywords = jieba.analyse.extract_tags(
        query,
        allowPOS=allow_pos,
    )

    keywords = list(dict.fromkeys([*keywords, query]))

    logger.info(f"抽取关键词: {keywords}")

    return {"keywords": keywords}
