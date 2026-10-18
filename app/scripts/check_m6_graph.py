"""M6 完整图级集成功能检查。"""

import asyncio
from datetime import date

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


async def main() -> None:
    """运行从关键词抽取到额外上下文的完整 M6 链路。"""

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
            context = DataAgentContext(
                embedding_client=(embedding_client_manager.client),
                column_qdrant_repository=(
                    ColumnQdrantRepository(qdrant_client_manager.client)
                ),
                metric_qdrant_repository=(
                    MetricQdrantRepository(qdrant_client_manager.client)
                ),
                value_es_repository=ValueESRepository(es_client_manager.client),
                meta_mysql_repository=MetaMySQLRepository(meta_session),
                dw_mysql_repository=DWMySQLRepository(dw_session),
            )

            state: DataAgentState = {
                "query": ("华东地区 iPhone 的销售总额是多少？"),
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
                "error": None,
            }

            result = await graph.ainvoke(
                input=state,
                context=context,
                interrupt_after=[
                    "add_extra_context",
                ],
            )

            table_infos = result["table_infos"]
            metric_infos = result["metric_infos"]

            table_info_map = {
                table_info["name"]: table_info for table_info in table_infos
            }
            table_names = set(table_info_map)

            expected_tables = {
                "dim_region",
                "dim_product",
                "fact_order",
            }

            if table_names != expected_tables:
                raise AssertionError(f"M6 过滤后的表不正确: {table_names}")

            column_names = {
                table_name: {
                    column_info["name"] for column_info in table_info["columns"]
                }
                for table_name, table_info in table_info_map.items()
            }

            required_columns = {
                "dim_region": {
                    "region_id",
                    "region_name",
                },
                "dim_product": {
                    "product_id",
                    "product_name",
                },
                "fact_order": {
                    "region_id",
                    "product_id",
                    "order_amount",
                },
            }

            for table_name, expected_columns in required_columns.items():
                missing_columns = expected_columns - column_names[table_name]

                if missing_columns:
                    raise AssertionError(f"{table_name} 缺少字段: {missing_columns}")

            metric_names = [metric_info["name"] for metric_info in metric_infos]

            if metric_names != ["GMV"]:
                raise AssertionError(f"M6 过滤后的指标不正确: {metric_names}")

            region_name_info = next(
                column_info
                for column_info in table_info_map["dim_region"]["columns"]
                if column_info["name"] == "region_name"
            )
            product_name_info = next(
                column_info
                for column_info in table_info_map["dim_product"]["columns"]
                if column_info["name"] == "product_name"
            )

            if "华东" not in region_name_info["examples"]:
                raise AssertionError("region_name.examples 缺少华东")

            if "iPhone 15 Pro" not in (product_name_info["examples"]):
                raise AssertionError("product_name.examples 缺少 iPhone 15 Pro")

            today = date.today()
            date_info = result["date_info"]
            db_info = result["db_info"]

            if date_info["date"] != (today.strftime("%Y-%m-%d")):
                raise AssertionError(f"日期不正确: {date_info}")

            if date_info["quarter"] != (f"Q{(today.month - 1) // 3 + 1}"):
                raise AssertionError(f"季度不正确: {date_info}")

            if db_info["dialect"] != "mysql":
                raise AssertionError(f"数据库方言不正确: {db_info}")

            if not db_info["version"]:
                raise AssertionError("数据库版本不能为空")

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
            print("过滤后的表:", list(table_info_map))
            print("过滤后的字段:", column_names)
            print("过滤后的指标:", metric_names)
            print("日期信息:", date_info)
            print("数据库信息:", db_info)
            print("M6 图级集成检查通过")
    finally:
        await dw_mysql_client_manager.close()
        await meta_mysql_client_manager.close()
        await es_client_manager.close()
        await embedding_client_manager.close()
        await qdrant_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
