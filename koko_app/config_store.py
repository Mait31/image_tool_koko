import json
import os

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


def load_koko_api_key():
    data = _load_config()
    return data.get("koko_api_key", "") or os.getenv("KOKO_API_KEY", "")


def save_koko_api_key(key):
    data = _load_config()
    data["koko_api_key"] = key
    return _save_config(data)


def load_koko_paths():
    data = _load_config()
    return {
        "excel_path": data.get("koko_excel_path", "") or "",
        "folder_path": data.get("koko_folder_path", "") or "",
    }


def save_koko_paths(*, excel_path=None, folder_path=None):
    data = _load_config()
    if excel_path is not None:
        data["koko_excel_path"] = excel_path
    if folder_path is not None:
        data["koko_folder_path"] = folder_path
    return _save_config(data)
