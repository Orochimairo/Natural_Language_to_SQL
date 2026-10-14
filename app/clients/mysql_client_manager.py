"""MySQL 客户端管理器。"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.conf.app_config import DBConfig, app_config


class MySQLClientManager:
    """管理 MySQL 异步 Engine 和 Session 工厂。"""

    def __init__(self, config: DBConfig):
        self.config = config
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def _get_url(self) -> str:
        """根据配置生成 MySQL 异步连接地址。"""
        return (
            f"mysql+asyncmy://{self.config.user}:{self.config.password}"
            f"@{self.config.host}:{self.config.port}/{self.config.database}"
            "?charset=utf8mb4"
        )

    @property
    def engine(self) -> AsyncEngine:
        """返回已初始化的异步 Engine。"""
        if self._engine is None:
            raise RuntimeError("MySQL Engine 尚未初始化")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """返回已初始化的 Session 工厂。"""
        if self._session_factory is None:
            raise RuntimeError("MySQL Session 工厂尚未初始化")
        return self._session_factory

    def init(self) -> None:
        """初始化异步 Engine 和 Session 工厂。"""
        if self._engine is not None or self._session_factory is not None:
            raise RuntimeError("MySQL 客户端已经初始化")

        engine = create_async_engine(
            self._get_url(),
            pool_size=10,
            pool_pre_ping=True,
        )
        session_factory = async_sessionmaker(
            engine,
            autoflush=True,
            expire_on_commit=False,
        )

        self._engine = engine
        self._session_factory = session_factory

    async def close(self) -> None:
        """释放 MySQL 连接池。"""
        engine = self.engine
        await engine.dispose()
        self._engine = None
        self._session_factory = None


meta_mysql_client_manager = MySQLClientManager(app_config.db_meta)
dw_mysql_client_manager = MySQLClientManager(app_config.db_dw)
