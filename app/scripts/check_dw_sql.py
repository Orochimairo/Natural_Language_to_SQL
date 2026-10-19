"""DW SQL 校验和执行功能检查。"""

import asyncio

from sqlalchemy.exc import SQLAlchemyError

from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
)
from app.repositories.mysql.dw.dw_mysql_repository import (
    DWMySQLRepository,
)


async def main() -> None:
    """连接真实 DW MySQL 检查 SQL 校验和查询执行。"""

    dw_mysql_client_manager.init()

    try:
        async with dw_mysql_client_manager.session_factory() as session:
            repository = DWMySQLRepository(session)

            valid_sql = """
                SELECT order_id, order_amount
                FROM fact_order
                ORDER BY order_id
                LIMIT 1
            """

            await repository.validate(valid_sql)
            print("合法 SQL 校验通过")

            rows = await repository.run(valid_sql)

            if not isinstance(rows, list):
                raise AssertionError("SQL 执行结果不是 list")

            if not rows:
                raise AssertionError("fact_order 查询结果为空")

            if not isinstance(rows[0], dict):
                raise AssertionError("SQL 查询行没有转换成 dict")

            expected_columns = {
                "order_id",
                "order_amount",
            }

            if set(rows[0]) != expected_columns:
                raise AssertionError(f"查询结果字段不正确: {set(rows[0])}")

            print("查询结果:", rows)

            invalid_sql = """
                SELECT not_existing_column
                FROM fact_order
            """

            try:
                await repository.validate(invalid_sql)
            except SQLAlchemyError as error:
                print("非法 SQL 正确抛出数据库异常:")
                print(type(error).__name__)
            else:
                raise AssertionError("非法 SQL 没有抛出数据库异常")
    finally:
        await dw_mysql_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
