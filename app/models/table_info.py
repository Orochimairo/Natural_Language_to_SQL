"""表元数据 ORM 模型。"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TableInfoMySQL(Base):
    """Meta MySQL 中的表元数据模型。"""

    __tablename__ = "table_info"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        comment="表编号",
    )
    name: Mapped[str | None] = mapped_column(
        String(128),
        comment="表名称",
    )
    role: Mapped[str | None] = mapped_column(
        String(32),
        comment="表类型",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        comment="表描述",
    )