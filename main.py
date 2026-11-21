"""
ITOps Command — console entry (diagnostics only).
Prefer gui.py / the windowed .exe for the product UI.
"""

from __future__ import annotations

import multiprocessing
import sys


def main() -> None:
    print("[*] Starting ITOps Assistant...")
    print("[*] Collecting system inventory...")

    from modules.inventory import get_inventory
    from modules.network import get_network_info
    from modules.processes import get_top_processes
    from modules.health import calculate_health
    from modules.root_cause import analyze_root_cause
    from modules.fix_plan import generate_fix_plan
    from modules.fix_engine import run_auto_fixes
    from modules.history import load_previous_report, compare_reports, save_report
    from modules.export import export_report
    from modules.formatter import print_inventory

    data: dict = {}

    print("[*] Getting inventory...")
    inventory = get_inventory()
    data["system"] = inventory["system"]
    data["cpu"] = inventory["cpu"]
    data["ram"] = inventory["ram"]
    data["disk"] = inventory["disk"]

    print("[*] Running network diagnostics...")
    data["network"] = get_network_info()

    print("[*] Analyzing processes...")
    data["processes"] = get_top_processes()

    print("[*] Calculating health score...")
    data["health"] = calculate_health(data["cpu"], data["ram"], data["disk"])

    print("[*] Analyzing root cause...")
    data["root_cause"] = analyze_root_cause(data)
    data["fix_plan"] = generate_fix_plan(data["root_cause"])

    print("[*] Running auto-fixes (if needed)...")
    data["auto_fixes"] = run_auto_fixes(data["root_cause"])

    print("[*] Security posture scan...")
    try:
        from modules.security import run_security_scan, format_text

        data["security"] = run_security_scan()
        print(format_text(data["security"]))
    except Exception as e:
        data["security"] = {"error": str(e), "findings": []}
        print(f"[!] Security scan skipped: {e}")

    print("[*] Checking history...")
    previous = load_previous_report()
    data["changes"] = compare_reports(data, previous)
    save_report(data)

    print("[*] Exporting reports...")
    data["export"] = export_report(data)

    print("[*] Generating report...\n")
    print_inventory(data)

    if data.get("export"):
        print(f"\n[*] JSON: {data['export'].get('json')}")
        print(f"[*] HTML: {data['export'].get('html')}")

    print("\n[*] Done.")
    if sys.stdin and sys.stdin.isatty():
        try:
            input("Press Enter to exit...")
        except EOFError:
            pass


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
