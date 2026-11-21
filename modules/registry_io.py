"""
Thin registry layer (winreg only — no subprocess, no localized text).

Kept separate so security checks can be unit-tested with a fake registry
and so every registry access is in one auditable place.
"""
from __future__ import annotations

import ctypes
from typing import Any

_HIVES = {"HKLM": "HKEY_LOCAL_MACHINE", "HKCU": "HKEY_CURRENT_USER"}


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:
        return False


class WinRegistry:
    """Real registry backend (Windows). Reads use the 64-bit view explicitly."""

    @staticmethod
    def _root(hive: str):
        import winreg

        return getattr(winreg, _HIVES[hive])

    def get(self, hive: str, path: str, name: str) -> Any:
        """Return the value, or None if the key/value does not exist."""
        import winreg

        try:
            with winreg.OpenKey(
                self._root(hive), path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY
            ) as k:
                return winreg.QueryValueEx(k, name)[0]
        except OSError:
            return None

    def key_exists(self, hive: str, path: str) -> bool:
        import winreg

        try:
            with winreg.OpenKey(
                self._root(hive), path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY
            ):
                return True
        except OSError:
            return False

    def list_values(self, hive: str, path: str) -> dict[str, Any]:
        import winreg

        out: dict[str, Any] = {}
        try:
            with winreg.OpenKey(
                self._root(hive), path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY
            ) as k:
                i = 0
                while True:
                    try:
                        n, v, _t = winreg.EnumValue(k, i)
                    except OSError:
                        break
                    out[n] = v
                    i += 1
        except OSError:
            pass
        return out

    def set_dword(self, hive: str, path: str, name: str, value: int) -> None:
        import winreg

        with winreg.CreateKeyEx(
            self._root(hive), path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
        ) as k:
            winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, int(value))

    def delete_value(self, hive: str, path: str, name: str) -> None:
        import winreg

        try:
            with winreg.OpenKey(
                self._root(hive), path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY
            ) as k:
                winreg.DeleteValue(k, name)
        except OSError:
            pass
