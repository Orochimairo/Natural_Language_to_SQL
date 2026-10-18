"""问数智能体的共享状态。"""

from typing import Any, TypedDict

from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.value_info import ValueInfo


class ColumnInfoState(TypedDict):
    """面向后续提示词的字段信息。"""

    name: str
    type: str
    role: str
    examples: list[Any]
    description: str
    alias: list[str]


class TableInfoState(TypedDict):
    """按表组织的字段上下文。"""

    name: str
    role: str
    description: str
    columns: list[ColumnInfoState]


class MetricInfoState(TypedDict):
    """面向后续提示词的指标信息。"""

    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]


class DateInfoState(TypedDict):
    """SQL 生成需要的当前日期信息。"""

    date: str
    weekday: str
    quarter: str


class DBInfoState(TypedDict):
    """SQL 生成需要的数据库环境信息。"""

    dialect: str
    version: str


class DataAgentState(TypedDict):
    """在 LangGraph 节点之间传递的业务状态。"""

    query: str
    keywords: list[str]

    retrieved_column_infos: list[ColumnInfo]
    retrieved_metric_infos: list[MetricInfo]
    retrieved_value_infos: list[ValueInfo]
    table_infos: list[TableInfoState]
    metric_infos: list[MetricInfoState]
    date_info: DateInfoState
    db_info: DBInfoState

    error: str | None
