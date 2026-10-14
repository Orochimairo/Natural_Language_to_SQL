"""请求上下文。"""

from contextvars import ContextVar

# ContextVar[str] 表示当前执行上下文中的 request_id 应为字符串。
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="1")
