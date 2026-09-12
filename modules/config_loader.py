import json
import os
import copy


DEFAULT_CONFIG = {
    "version": "1.0",
    "thresholds": {
        "cpu_warning": 70,
        "cpu_critical": 90,
        "ram_warning": 75,
        "ram_critical": 90,
        "disk_warning": 70,
        "disk_high": 85,
        "disk_critical": 95,
        "history_cpu_change": 10,
        "history_ram_change": 8,
        "history_disk_change": 3,
        "history_gateway_latency_change": 5,
        "history_internet_latency_change": 15
    },
    "auto_fix": {
        "enabled": True,
        "flush_dns": True,
        "restart_dns_client": True,
        "clean_temp": True,
        "empty_recycle_bin": True,
        "disk_cleanup": True
    },
    "export": {
        "enabled": True,
        "json": True,
        "html": True,
        "folder": "reports"
    },
    "history": {
        "enabled": True,
        "file": "last_report.json"
    },
    "display": {
        "show_processes": True,
        "show_auto_fixes": True,
        "show_changes": True,
        "process_limit": 5
    }
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(config_path: str | None = None) -> dict:
    """
    Load configuration.
    Priority:
      1. Explicit path passed by CLI
      2. config.json next to main.py / project root
      3. Built-in defaults
    """
    config = copy.deepcopy(DEFAULT_CONFIG)

    # Determine candidate paths
    candidates = []

    if config_path:
        candidates.append(config_path)

    # Project root (parent of modules/)
    try:
        modules_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(modules_dir)
        candidates.append(os.path.join(project_root, "config.json"))
    except Exception:
        pass

    # Current working directory
    candidates.append(os.path.join(os.getcwd(), "config.json"))

    for path in candidates:
        if path and os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                config = _deep_merge(config, user_config)
                config["_loaded_from"] = path
                return config
            except (OSError, json.JSONDecodeError):
                continue

    config["_loaded_from"] = "defaults"
    return config
