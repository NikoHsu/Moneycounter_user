"""
配置加载模块 - 从 YAML 文件读取规则配置

设计原则：
- 规则外置，修改 YAML 即可调整行为
- 支持多配置合并（默认配置 + 用户自定义）
"""

import os
import yaml

# 默认配置路径
DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "rules.yaml",
)


def load_config(config_path: str = None) -> dict:
    path = config_path or DEFAULT_CONFIG_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"配置文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config or {}


def get_config(config_path: str = None, force_reload: bool = False) -> dict:
    """获取配置（带缓存）"""
    path = config_path or DEFAULT_CONFIG_PATH
    if force_reload or path not in _config_cache:
        _config_cache[path] = load_config(path)
    return _config_cache[path]


_config_cache = {}
