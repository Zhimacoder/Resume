"""
配置管理模块
负责模型配置的加密存储和读取
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import base64
import hashlib

# 配置文件路径
CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "models.json.enc"
CONFIG_KEY_FILE = CONFIG_DIR / ".key"

# 默认模型配置
DEFAULT_MODELS = {
    "doubao": {
        "model_name": "字节豆包",
        "api_key": "",
        "endpoint": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "model_version": "",
        "is_valid": False
    },
    "wenxin": {
        "model_name": "百度文心",
        "api_key": "",
        "endpoint": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions",
        "model_version": "",
        "is_valid": False
    },
    "qianwen": {
        "model_name": "阿里千问",
        "api_key": "",
        "endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "model_version": "",
        "is_valid": False
    },
    "zhipu": {
        "model_name": "智谱GLM",
        "api_key": "",
        "endpoint": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "model_version": "",
        "is_valid": False
    },
    "minmax": {
        "model_name": "MinMax",
        "api_key": "",
        "endpoint": "https://api.minimax.chat/v1/text/chatcompletion_v2",
        "model_version": "",
        "is_valid": False
    },
    "custom": {
        "model_name": "自定义大模型",
        "api_key": "",
        "endpoint": "",
        "model_version": "",
        "is_valid": False
    }
}

DEFAULT_CONFIG = {
    "current_model": "doubao",
    "is_config_valid": False,
    "models": DEFAULT_MODELS
}


def _get_cipher() -> Fernet:
    """获取加密解密器"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if CONFIG_KEY_FILE.exists():
        with open(CONFIG_KEY_FILE, 'rb') as f:
            key = f.read()
    else:
        key = Fernet.generate_key()
        with open(CONFIG_KEY_FILE, 'wb') as f:
            f.write(key)

    return Fernet(key)


def load_config() -> Dict[str, Any]:
    """加载配置"""
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()

    try:
        cipher = _get_cipher()
        with open(CONFIG_FILE, 'rb') as f:
            encrypted_data = f.read()

        decrypted_data = cipher.decrypt(encrypted_data)
        config = json.loads(decrypted_data)

        # 合并默认配置，确保字段完整
        config = {**DEFAULT_CONFIG, **config}
        for model_key, model_data in DEFAULT_MODELS.items():
            if model_key in config.get("models", {}):
                config["models"][model_key] = {**model_data, **config["models"][model_key]}
            else:
                config["models"][model_key] = model_data

        return config
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> bool:
    """保存配置"""
    try:
        cipher = _get_cipher()
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # 验证配置有效性
        current_model = config.get("current_model", "doubao")
        model_config = config.get("models", {}).get(current_model, {})

        api_key = model_config.get("api_key", "")
        endpoint = model_config.get("endpoint", "")

        config["is_config_valid"] = bool(api_key and endpoint)

        if current_model in config["models"]:
            config["models"][current_model]["is_valid"] = config["is_config_valid"]

        json_data = json.dumps(config, ensure_ascii=False, indent=2)
        encrypted_data = cipher.encrypt(json_data.encode())

        with open(CONFIG_FILE, 'wb') as f:
            f.write(encrypted_data)

        return True
    except Exception as e:
        print(f"保存配置失败: {e}")
        return False


def get_config_status() -> Dict[str, Any]:
    """获取配置状态"""
    config = load_config()
    return {
        "is_config_valid": config.get("is_config_valid", False),
        "current_model": config.get("current_model", "doubao"),
        "models": config.get("models", {})
    }


def validate_model_config(model_key: str, api_key: str, endpoint: str) -> bool:
    """验证模型配置是否有效"""
    return bool(api_key and endpoint)
