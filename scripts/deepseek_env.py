"""读取模型 API 环境变量。

脚本用途：在未安装 python-dotenv 时，仍能读取简单的 `.env` 键值对。
流程阶段：公共配置。
主要输入：`.env` 文件或调用方显式传入的路径。
主要输出：写入 `os.environ` 的环境变量。
重要边界：本脚本只负责加载环境变量，不判断研究流程、题库来源或绘图要求。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


# ===== 环境变量加载 =====

def load_dotenv(path: str | os.PathLike[str] | None = None, *args: Any, **kwargs: Any) -> bool:
    """优先调用 python-dotenv；缺少依赖时读取简单的 KEY=VALUE 行。"""
    try:
        from dotenv import load_dotenv as real_load_dotenv

        return bool(real_load_dotenv(path, *args, **kwargs))
    except ModuleNotFoundError:
        if path is None:
            path = ".env"
        env_path = Path(path)
        if not env_path.exists():
            return False
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
        return True
