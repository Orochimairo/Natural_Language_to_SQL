"""SQLAlchemy ORM 声明式基类。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """项目中所有 Meta MySQL ORM 模型的公共基类."""

    pass