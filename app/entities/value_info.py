"""字段真实值业务实体。"""

from dataclasses import dataclass


@dataclass
class ValueInfo:
    """一个字段真实值及其所属字段。"""

    id: str
    value: str
    column_id: str