"""问数智能体的共享状态。"""

from typing import TypedDict

from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.value_info import ValueInfo


class DataAgentState(TypedDict):
    """在 LangGraph 节点之间传递的业务状态。"""

    query: str
    keywords: list[str]

    retrieved_column_infos: list[ColumnInfo]
    retrieved_metric_infos: list[MetricInfo]
    retrieved_value_infos: list[ValueInfo]

    error: str | None
