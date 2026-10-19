"""M7 完整生产图级集成功能检查。"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.state import DataAgentState
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


class RecordingDWMySQLRepository(DWMySQLRepository):
    """执行真实查询并记录最终 SQL 和结果。"""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.executed_sqls: list[str] = []
        self.results: list[list[dict]] = []

    async def run(self, sql: str) -> list[dict]:
        """调用真实查询并记录结果。"""

        result = await super().run(sql)

        self.executed_sqls.append(sql)
        self.results.append(result)

        return result


async def main() -> None:
    """从自然语言问题开始运行完整生产图。"""

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
            dw_repository = RecordingDWMySQLRepository(dw_session)

            context = DataAgentContext(
                embedding_client=embedding_client_manager.client,
                column_qdrant_repository=ColumnQdrantRepository(
                    qdrant_client_manager.client
                ),
                metric_qdrant_repository=MetricQdrantRepository(
                    qdrant_client_manager.client
                ),
                value_es_repository=ValueESRepository(es_client_manager.client),
                meta_mysql_repository=MetaMySQLRepository(meta_session),
                dw_mysql_repository=dw_repository,
            )

            state: DataAgentState = {
                "query": "华东地区 iPhone 的销售总额是多少？",
                "keywords": [],
                "retrieved_column_infos": [],
                "retrieved_metric_infos": [],
                "retrieved_value_infos": [],
                "table_infos": [],
                "metric_infos": [],
                "date_info": {
                    "date": "",
                    "weekday": "",
                    "quarter": "",
                },
                "db_info": {
                    "dialect": "",
                    "version": "",
                },
                "sql": "",
                "error": None,
            }

            result = await graph.ainvoke(
                input=state,
                context=context,
            )

            if not result["retrieved_column_infos"]:
                raise AssertionError("完整图没有召回字段")

            if not result["retrieved_metric_infos"]:
                raise AssertionError("完整图没有召回指标")

            if not result["retrieved_value_infos"]:
                raise AssertionError("完整图没有召回字段值")

            if not result["table_infos"]:
                raise AssertionError("完整图没有生成表上下文")

            metric_names = [
                metric_info["name"] for metric_info in result["metric_infos"]
            ]

            if "GMV" not in metric_names:
                raise AssertionError(f"过滤后的指标缺少 GMV: {metric_names}")

            db_info = result["db_info"]

            if db_info["dialect"] != "mysql":
                raise AssertionError(f"数据库方言不正确: {db_info}")

            if not db_info["version"]:
                raise AssertionError("数据库版本不能为空")

            sql = result["sql"]

            if not isinstance(sql, str) or not sql.strip():
                raise AssertionError("完整图没有生成非空 SQL")

            if "```" in sql:
                raise AssertionError("最终 SQL 包含 Markdown 代码块")

            normalized_sql = sql.lstrip().upper()

            if not normalized_sql.startswith(
                (
                    "SELECT",
                    "WITH",
                )
            ):
                raise AssertionError(f"最终结果不是查询 SQL: {sql}")

            if len(dw_repository.executed_sqls) != 1:
                raise AssertionError("完整图没有且仅执行一次最终 SQL")

            executed_sql = dw_repository.executed_sqls[0]

            if executed_sql != sql:
                raise AssertionError("最终执行的 SQL 与 State 中的 SQL 不一致")

            if len(dw_repository.results) != 1:
                raise AssertionError("完整图没有记录一次查询结果")

            query_result = dw_repository.results[0]

            if not query_result:
                raise AssertionError("最终查询结果为空")

            result_row = query_result[0]

            if not isinstance(result_row, dict):
                raise AssertionError("最终查询行不是 dict")

            if len(result_row) != 1:
                raise AssertionError(f"聚合查询应返回一个结果列: {result_row}")

            result_column, result_value = next(iter(result_row.items()))

            if not isinstance(result_column, str) or not result_column.strip():
                raise AssertionError(f"聚合结果列别名无效: {result_column!r}")

            if result_value is None:
                raise AssertionError(f"聚合查询结果不能为空: {result_row}")

            if result["error"] is None:
                sql_branch = "生成 SQL 校验通过后直接执行"
            else:
                sql_branch = "生成 SQL 校验失败，校正后执行"

            print(
                "召回字段:",
                [column_info.id for column_info in result["retrieved_column_infos"]],
            )
            print(
                "召回指标:",
                [metric_info.id for metric_info in result["retrieved_metric_infos"]],
            )
            print(
                "召回字段值:",
                [value_info.id for value_info in result["retrieved_value_infos"]],
            )
            print(
                "过滤后的表:",
                [table_info["name"] for table_info in result["table_infos"]],
            )
            print("过滤后的指标:", metric_names)
            print("日期信息:", result["date_info"])
            print("数据库信息:", db_info)
            print("SQL 分支:", sql_branch)

            if result["error"] is not None:
                print("原 SQL 校验错误:", result["error"])

            print("最终 SQL:")
            print(sql)
            print("最终查询结果:", query_result)
            print("结果列别名:", result_column)
            print("结果值:", result_value)
            print("M7 完整图级集成检查通过")
    finally:
        await dw_mysql_client_manager.close()
        await meta_mysql_client_manager.close()
        await es_client_manager.close()
        await embedding_client_manager.close()
        await qdrant_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
