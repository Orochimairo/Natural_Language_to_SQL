"""应用主配置的数据结构。"""

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from omegaconf import OmegaConf


@dataclass
class File:
    """文件日志配置"""

    enable: bool
    level: str
    path: str
    rotation: str
    retention: str


@dataclass
class Console:
    """控制台日志配置"""

    enable: bool
    level: str


@dataclass
class LoggingConfig:
    """日志配置"""

    file: File
    console: Console


@dataclass
class DBConfig:
    """数据库配置"""

    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class QdrantConfig:
    """Qdrant连接配置"""

    host: str
    port: int
    embedding_size: int


@dataclass
class EmbeddingConfig:
    """向量嵌入配置"""

    host: str
    port: int
    model: str


@dataclass
class ESConfig:
    """Elasticsearch连接配置"""

    host: str
    port: int
    index_name: str


@dataclass
class LLMConfig:
    """大语言模型配置"""

    model_name: str
    api_key: str
    base_url: str


@dataclass
class AppConfig:
    """项目级配置入口"""

    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm: LLMConfig


project_root = Path(__file__).parents[2]
config_file = project_root / "conf" / "app_config.yaml"

load_dotenv(project_root / ".env")

context = OmegaConf.load(config_file)
schema = OmegaConf.structured(AppConfig)

app_config: AppConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))
