"""Run Windows commands with NO visible console window."""

from __future__ import annotations

import subprocess
import sys
from typing import Sequence

# Hide console for child processes (Windows)
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
DETACHED_PROCESS = 0x00000008
SW_HIDE = 0


def _hidden_kwargs() -> dict:
    if sys.platform != "win32":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = SW_HIDE
    return {
        "startupinfo": startupinfo,
        "creationflags": CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
    }


def run_silent(
    args: Sequence[str] | str,
    *,
    timeout: float = 30,
    shell: bool = False,
) -> subprocess.CompletedProcess[str]:
    # Never shell=True — that spawns visible cmd.exe
    if isinstance(args, str):
        args = args.split()
    try:
        return subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            **_hidden_kwargs(),
        )
    except subprocess.TimeoutExpired as e:
        return subprocess.CompletedProcess(
            list(args),
            returncode=124,
            stdout=(e.stdout or "") if isinstance(e.stdout, str) else "",
            stderr="timeout",
        )


def run_powershell(script: str, *, timeout: float = 60) -> subprocess.CompletedProcess[str]:
    # Prefer powershell with explicit hidden window + CREATE_NO_WINDOW
    return run_silent(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-WindowStyle",
            "Hidden",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        timeout=timeout,
        shell=False,
    )
