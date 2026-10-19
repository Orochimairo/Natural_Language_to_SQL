"""QueryService 真实工作流功能检查。"""

import asyncio
import json

from app.clients.embedding_client_manager import (
    embedding_client_manager,
)
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
    meta_mysql_client_manager,
)
from app.clients.qdrant_client_manager import (
    qdrant_client_manager,
)
from app.repositories.es.value_es_repository import (
    ValueESRepository,
)
from app.repositories.mysql.dw.dw_mysql_repository import (
    DWMySQLRepository,
)
from app.repositories.mysql.meta.meta_mysql_repository import (
    MetaMySQLRepository,
)
from app.repositories.qdrant.column_qdrant_repository import (
    ColumnQdrantRepository,
)
from app.repositories.qdrant.metric_qdrant_repository import (
    MetricQdrantRepository,
)
from app.services.query_service import QueryService


async def main() -> None:
    """运行真实 LangGraph 并检查 SSE 消息。"""

    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()

    try:
        async with (
            meta_mysql_client_manager.session_factory() as meta_session,
            dw_mysql_client_manager.session_factory() as dw_session,
        ):
            query_service = QueryService(
                meta_mysql_repository=MetaMySQLRepository(meta_session),
                embedding_client=embedding_client_manager.client,
                dw_mysql_repository=DWMySQLRepository(dw_session),
                column_qdrant_repository=ColumnQdrantRepository(
                    qdrant_client_manager.client
                ),
                metric_qdrant_repository=MetricQdrantRepository(
                    qdrant_client_manager.client
                ),
                value_es_repository=ValueESRepository(es_client_manager.client),
            )

            messages = [
                message
                async for message in query_service.query(
                    "华东地区 iPhone 的销售总额是多少？"
                )
            ]

            if not messages:
                raise AssertionError("QueryService 没有输出 SSE 消息")

            events: list[dict] = []

            for message in messages:
                if not message.startswith("data: "):
                    raise AssertionError(f"SSE 消息缺少 data 前缀: {message!r}")

                if not message.endswith("\n\n"):
                    raise AssertionError(f"SSE 消息缺少结尾空行: {message!r}")

                payload = message.removeprefix("data: ").removesuffix("\n\n")

                event = json.loads(payload)

                if not isinstance(event, dict):
                    raise AssertionError(f"SSE 数据不是 JSON 对象: {event}")

                events.append(event)

            error_events = [event for event in events if event.get("type") == "error"]

            if error_events:
                raise AssertionError(f"工作流返回错误事件: {error_events}")

            progress_events = [
                event for event in events if event.get("type") == "progress"
            ]

            result_events = [event for event in events if event.get("type") == "result"]

            if not progress_events:
                raise AssertionError("没有收到进度事件")

            if len(result_events) != 1:
                raise AssertionError(f"预期一个结果事件，实际为: {result_events}")

            progress_steps = {event.get("step") for event in progress_events}

            required_steps = {
                "抽取关键词",
                "召回字段信息",
                "召回指标信息",
                "召回字段取值",
                "合并召回信息",
                "过滤表信息",
                "过滤指标信息",
                "添加额外上下文",
                "生成SQL",
                "校验SQL",
                "执行SQL",
            }

            missing_steps = required_steps - progress_steps

            if missing_steps:
                raise AssertionError(f"缺少进度步骤: {missing_steps}")

            query_result = result_events[0].get("data")

            if not isinstance(query_result, list):
                raise AssertionError(f"查询结果不是列表: {query_result}")

            if not query_result:
                raise AssertionError("最终查询结果为空")

            if not isinstance(query_result[0], dict):
                raise AssertionError(f"查询结果行不是字典: {query_result[0]}")

            print("进度步骤:", progress_steps)
            print("最终结果事件:", result_events[0])
            print("SSE 消息数量:", len(messages))
            print("QueryService 真实工作流检查通过")
    finally:
        await dw_mysql_client_manager.close()
        await meta_mysql_client_manager.close()
        await es_client_manager.close()
        await embedding_client_manager.close()
        await qdrant_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
