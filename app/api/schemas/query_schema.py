"""问数查询接口的请求体结构。"""

from pydantic import BaseModel


class QuerySchema(BaseModel):
    """接收用户输入的自然语言问题。校验模型，保证前端发送到后端的json数据必须符合这个结构，否则后端拒绝请求"""

    query: str
