import subprocess
import os
import tempfile
from datetime import datetime


def _run_command(cmd, shell=False, timeout=45):
    """Run a command safely and return success + output."""
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="ignore"
        )
        return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
    except (subprocess.TimeoutExpired, OSError) as e:
        return False, str(e)


def flush_dns():
    """Flush DNS cache."""
    success, output = _run_command(["ipconfig", "/flushdns"])
    return {
        "action": "Flush DNS cache",
        "success": success,
        "details": output if success else "Failed to flush DNS"
    }


def restart_dns_client():
    """Restart the DNS Client service (stronger than flush)."""
    # Stop then start
    stop_ok, _ = _run_command(["net", "stop", "Dnscache"])
    start_ok, output = _run_command(["net", "start", "Dnscache"])

    success = start_ok
    details = "DNS Client service restarted successfully" if success else "Failed to restart DNS Client service (may need Admin)"

    return {
        "action": "Restart DNS Client service",
        "success": success,
        "details": details
    }


def clean_user_temp():
    """
    Clean current user's TEMP folder (safe).
    Only deletes files, ignores folders that are locked.
    """
    temp_dir = tempfile.gettempdir()
    deleted = 0
    errors = 0

    try:
        for root, dirs, files in os.walk(temp_dir):
            for name in files:
                try:
                    file_path = os.path.join(root, name)
                    # Skip very recent files (last 10 minutes)
                    if os.path.getmtime(file_path) > (datetime.now().timestamp() - 600):
                        continue
                    os.remove(file_path)
                    deleted += 1
                except (PermissionError, OSError):
                    errors += 1
    except Exception:
        pass

    return {
        "action": "Clean user TEMP folder",
        "success": True,
        "details": f"Deleted {deleted} files (skipped {errors} locked files)"
    }


def empty_recycle_bin():
    """Empty the Recycle Bin for all drives."""
    # PowerShell is the most reliable way
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
    ]
    success, output = _run_command(cmd, timeout=60)

    return {
        "action": "Empty Recycle Bin",
        "success": success,
        "details": "Recycle Bin emptied" if success else "Failed to empty Recycle Bin (may need Admin or already empty)"
    }


def run_disk_cleanup():
    """
    Run Windows Disk Cleanup in silent mode.
    Uses sagerun if previously configured, otherwise falls back to basic cleanmgr.
    """
    # First try to set up common cleanup options then run
    # This is a simplified safe version
    success, output = _run_command(
        ["cleanmgr", "/d", "C:", "/VERYLOWDISK"],
        timeout=120
    )

    # Alternative lighter approach if the above fails
    if not success:
        success, output = _run_command(
            ["cleanmgr", "/sagerun:1"],
            timeout=120
        )

    return {
        "action": "Run Disk Cleanup (silent)",
        "success": success,
        "details": "Disk Cleanup started" if success else "Disk Cleanup could not start (may need user interaction or Admin)"
    }


def run_auto_fixes(root_cause):
    """
    Execute safe automatic fixes based on detected issues.
    Returns list of actions performed.
    """
    results = []
    issues = root_cause.get("issues", [])

    # ---------- Network / DNS ----------
    dns_issues = any("DNS" in issue for issue in issues)
    network_issues = any(
        keyword in issue
        for issue in issues
        for keyword in ["Internet", "Gateway", "connectivity"]
    )

    if dns_issues or network_issues:
        results.append(flush_dns())
        if dns_issues:
            results.append(restart_dns_client())

    # ---------- Disk related ----------
    disk_issues = any("disk" in issue.lower() for issue in issues)

    if disk_issues:
        results.append(clean_user_temp())
        results.append(empty_recycle_bin())
        results.append(run_disk_cleanup())

    return results
