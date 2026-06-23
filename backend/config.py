"""
配置管理模块
负责模型配置的加密存储和读取
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet

# 配置文件路径
CONFIG_DIR = Path(__file__).parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "models.json.enc"
# 密钥存储到用户系统级目录，与密文物理隔离
CONFIG_KEY_DIR = Path.home() / ".config" / "resume_screening"
CONFIG_KEY_FILE = CONFIG_KEY_DIR / ".key"

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
        "api_secret": "",
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
    "deepseek": {
        "model_name": "DeepSeek",
        "api_key": "",
        "endpoint": "https://api.deepseek.com/chat/completions",
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
    CONFIG_KEY_DIR.mkdir(parents=True, exist_ok=True)

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


def _is_model_config_valid(model_key: str, model_config: Dict[str, Any]) -> bool:
    """判断单个模型配置是否有效"""
    api_key = model_config.get("api_key", "")
    endpoint = model_config.get("endpoint", "")
    if not api_key or not endpoint:
        return False
    if model_key == "wenxin":
        api_secret = model_config.get("api_secret", "")
        if not api_secret:
            return False
    return True


def _is_masked(value: str) -> bool:
    """判断值是否为脱敏格式"""
    return bool(value) and "****" in value


def save_config(config: Dict[str, Any]) -> bool:
    """保存配置（智能合并：脱敏格式的字段保留原值）"""
    try:
        cipher = _get_cipher()
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        existing = load_config() if CONFIG_FILE.exists() else DEFAULT_CONFIG.copy()

        current_model = config.get("current_model", "doubao")
        new_models = config.get("models", {})
        existing_models = existing.get("models", {})

        merged_models = {}
        for model_key in set(list(existing_models.keys()) + list(new_models.keys())):
            existing_m = existing_models.get(model_key, {})
            new_m = new_models.get(model_key, {})
            merged = {**existing_m, **new_m}

            if new_m:
                if "api_key" in new_m and _is_masked(new_m.get("api_key", "")):
                    merged["api_key"] = existing_m.get("api_key", "")
                if "api_secret" in new_m and _is_masked(new_m.get("api_secret", "")):
                    merged["api_secret"] = existing_m.get("api_secret", "")

            for default_key, default_val in DEFAULT_MODELS.get(model_key, {}).items():
                if default_key not in merged:
                    merged[default_key] = default_val

            merged_models[model_key] = merged

        config["models"] = merged_models
        model_config = merged_models.get(current_model, {})

        config["is_config_valid"] = _is_model_config_valid(current_model, model_config)

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
    models = {}
    for model_key, model_data in config.get("models", {}).items():
        models[model_key] = {
            "model_name": model_data.get("model_name", ""),
            "endpoint": model_data.get("endpoint", ""),
            "is_valid": model_data.get("is_valid", False),
            "model_version": model_data.get("model_version", ""),
            "has_api_key": bool(model_data.get("api_key", "")),
            "has_api_secret": bool(model_data.get("api_secret", ""))
        }
    return {
        "is_config_valid": config.get("is_config_valid", False),
        "current_model": config.get("current_model", "doubao"),
        "models": models
    }


def get_masked_config() -> Dict[str, Any]:
    """获取脱敏后的配置（不返回明文 API Key）"""
    config = load_config()
    models = {}
    for model_key, model_data in config.get("models", {}).items():
        masked = {
            "model_name": model_data.get("model_name", ""),
            "endpoint": model_data.get("endpoint", ""),
            "is_valid": model_data.get("is_valid", False),
            "model_version": model_data.get("model_version", ""),
            "api_key": _mask_secret(model_data.get("api_key", "")),
        }
        if "api_secret" in model_data:
            masked["api_secret"] = _mask_secret(model_data.get("api_secret", ""))
        models[model_key] = masked
    return {
        "current_model": config.get("current_model", "doubao"),
        "is_config_valid": config.get("is_config_valid", False),
        "models": models
    }


def _mask_secret(secret: str) -> str:
    """对密钥进行脱敏显示"""
    if not secret:
        return ""
    if len(secret) <= 8:
        return "*" * len(secret)
    return secret[:4] + "****" + secret[-4:]


def validate_model_config(model_key: str, api_key: str, endpoint: str, api_secret: str = "") -> bool:
    """验证模型配置是否有效"""
    if not api_key or not endpoint:
        return False
    if model_key == "wenxin" and not api_secret:
        return False
    return True
