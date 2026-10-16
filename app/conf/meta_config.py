"""元数据知识构建配置。"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ColumnConfig:
    """单个字段的知识构建配置。"""

    name: str
    role: str
    description: str
    alias: list[str]
    sync: bool


@dataclass
class TableConfig:
    """单张表及其字段的知识构建配置。"""

    name: str
    role: str
    description: str
    columns: list[ColumnConfig]


@dataclass
class MetricConfig:
    """单个业务指标的知识构建配置"""

    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]


@dataclass
class MetaConfig:
    """一次元数据知识构建的完整配置。"""

    tables: Optional[list[TableConfig]] = None
    metrics: Optional[list[MetricConfig]] = None
