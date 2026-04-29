import json

from .config import CONFIG_PATH


def _load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_config(data):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def load_api_key():
    return _load_config().get("pipellm_api_key", "")


def save_api_key(key):
    data = _load_config()
    data["pipellm_api_key"] = key
    return _save_config(data)
