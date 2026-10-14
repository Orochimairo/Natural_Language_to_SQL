"""统一日志配置。"""

import sys
from pathlib import Path

from loguru import logger as loguru_logger

from app.conf.app_config import app_config
from app.core.context import request_id_ctx_var

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<magenta>request_id - {extra[request_id]}</magenta> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

PROJECT_ROOT = Path(__file__).parents[2]


def inject_request_id(record):
    """把当前上下文的 request_id 注入日志记录。

    Loguru 创建 record 后、交给输出处理器前调用此函数。
    """
    record["extra"]["request_id"] = request_id_ctx_var.get()


# 删除 Loguru 默认处理器，避免与项目控制台处理器重复输出。
loguru_logger.remove()

# 为每条日志记录注册 request_id 注入回调。
logger = loguru_logger.patch(inject_request_id)

if app_config.logging.console.enable:
    logger.add(
        sink=sys.stdout,
        level=app_config.logging.console.level,
        format=LOG_FORMAT,
    )

if app_config.logging.file.enable:
    log_directory = PROJECT_ROOT / app_config.logging.file.path
    log_directory.mkdir(parents=True, exist_ok=True)

    logger.add(
        sink=log_directory / "app.log",
        level=app_config.logging.file.level,
        format=LOG_FORMAT,
        rotation=app_config.logging.file.rotation,
        retention=app_config.logging.file.retention,
        encoding="utf-8",
    )
