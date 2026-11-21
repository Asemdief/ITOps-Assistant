"""Application and per-user data directories (source + frozen exe)."""

from __future__ import annotations

import os
import sys


def get_app_dir() -> str:
    """Directory of the app (exe folder when frozen, project root in source)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    modules_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(modules_dir)


def get_data_dir() -> str:
    """
    Writable per-user data dir for journals and non-report state.

    Prefer %LOCALAPPDATA%\\ITOps-Command on Windows so Program Files installs
    can still write. Fall back to <app>/data when LOCALAPPDATA is missing.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            path = os.path.join(base, "ITOps-Command")
        else:
            path = os.path.join(get_app_dir(), "data")
    else:
        path = os.path.join(
            os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"),
            "ITOps-Command",
        )
    os.makedirs(path, exist_ok=True)
    return path


def get_reports_dir() -> str:
    """Reports stay next to the app for easy discovery."""
    path = os.path.join(get_app_dir(), "reports")
    os.makedirs(path, exist_ok=True)
    return path
