"""DW 数据库信息查询功能检查。"""

import asyncio

from app.clients.mysql_client_manager import (
    dw_mysql_client_manager,
)
from app.repositories.mysql.dw.dw_mysql_repository import (
    DWMySQLRepository,
)


async def main() -> None:
    """连接真实 DW MySQL 并读取方言和版本。"""

    dw_mysql_client_manager.init()

    try:
        async with dw_mysql_client_manager.session_factory() as session:
            repository = DWMySQLRepository(session)
            db_info = await repository.get_db_info()

            if db_info["dialect"] != "mysql":
                raise AssertionError(f"数据库方言不是 mysql: {db_info['dialect']}")

            if not db_info["version"]:
                raise AssertionError("数据库版本不能为空")

            print("数据库方言:", db_info["dialect"])
            print("数据库版本:", db_info["version"])
    finally:
        await dw_mysql_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
