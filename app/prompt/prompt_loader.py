"""Prompt 模板加载工具。"""

from pathlib import Path


def load_prompt(name: str) -> str:
    """从项目 prompts 目录读取指定的 Prompt 文件。"""

    prompt_path = Path(__file__).parents[2] / "prompts" / f"{name}.prompt"
    return prompt_path.read_text(encoding="utf-8")
