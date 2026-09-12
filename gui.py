"""
ITOps Assistant - GUI Frontend
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime


def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class ITOpsApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("ITOps Assistant v1.2")
        self.geometry("920x640")
        self.minsize(800, 520)
        self.configure(bg="#0f172a")

        # Colors
        self.bg = "#0f172a"
        self.card = "#1e293b"
        self.accent = "#38bdf8"
        self.text = "#e2e8f0"
        self.muted = "#94a3b8"
        self.ok = "#4ade80"
        self.warn = "#fbbf24"
        self.bad = "#f87171"

        self._build_ui()
        self.scan_running = False

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=self.bg)
        header.pack(fill="x", padx=20, pady=(16, 8))

        title = tk.Label(
            header,
            text="ITOps Assistant",
            font=("Segoe UI", 20, "bold"),
            fg=self.accent,
            bg=self.bg,
        )
        title.pack(side="left")

        version = tk.Label(
            header,
            text="v1.2  •  System Diagnostics & Auto-Fix",
            font=("Segoe UI", 10),
            fg=self.muted,
            bg=self.bg,
        )
        version.pack(side="left", padx=(12, 0), pady=(8, 0))

        # Toolbar
        toolbar = tk.Frame(self, bg=self.bg)
        toolbar.pack(fill="x", padx=20, pady=(4, 10))

        self.btn_scan = tk.Button(
            toolbar,
            text="  Run Scan  ",
            font=("Segoe UI", 11, "bold"),
            bg="#0284c7",
            fg="white",
            activebackground="#0369a1",
            activeforeground="white",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.start_scan,
        )
        self.btn_scan.pack(side="left")

        self.btn_reports = tk.Button(
            toolbar,
            text="  Open Reports  ",
            font=("Segoe UI", 10),
            bg=self.card,
            fg=self.text,
            activebackground="#334155",
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
            command=self.open_reports,
        )
        self.btn_reports.pack(side="left", padx=(10, 0))

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(
            toolbar,
            textvariable=self.status_var,
            font=("Segoe UI", 10),
            fg=self.muted,
            bg=self.bg,
        )
        self.status_label.pack(side="right")

        # Report area
        frame = tk.Frame(self, bg=self.card)
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        self.output = scrolledtext.ScrolledText(
            frame,
            font=("Consolas", 10),
            bg="#0b1220",
            fg=self.text,
            insertbackground=self.text,
            relief="flat",
            padx=12,
            pady=12,
            wrap="word",
        )
        self.output.pack(fill="both", expand=True, padx=2, pady=2)

        self.output.insert("end", "Welcome to ITOps Assistant v1.2\n")
        self.output.insert("end", "Click « Run Scan » to start diagnostics.\n")
        self.output.configure(state="disabled")

        # Footer
        footer = tk.Label(
            self,
            text="ITOps Tools  •  Reports saved next to the application",
            font=("Segoe UI", 8),
            fg="#64748b",
            bg=self.bg,
        )
        footer.pack(pady=(0, 10))

    def log(self, text: str):
        self.output.configure(state="normal")
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")
        self.update_idletasks()

    def clear_output(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def set_status(self, text: str, color=None):
        self.status_var.set(text)
        self.status_label.configure(fg=color or self.muted)

    def start_scan(self):
        if self.scan_running:
            return
        self.scan_running = True
        self.btn_scan.configure(state="disabled", text="  Scanning...  ")
        self.clear_output()
        self.set_status("Running...", self.accent)

        thread = threading.Thread(target=self.run_scan, daemon=True)
        thread.start()

    def run_scan(self):
        try:
            self.log("[*] Starting system diagnostics...")

            from modules.inventory import get_inventory
            from modules.network import get_network_info
            from modules.processes import get_top_processes
            from modules.health import calculate_health
            from modules.root_cause import analyze_root_cause
            from modules.fix_plan import generate_fix_plan
            from modules.fix_engine import run_auto_fixes
            from modules.history import load_previous_report, compare_reports, save_report
            from modules.export import export_report

            data = {}

            self.log("[*] Collecting inventory...")
            inventory = get_inventory()
            data["system"] = inventory["system"]
            data["cpu"] = inventory["cpu"]
            data["ram"] = inventory["ram"]
            data["disk"] = inventory["disk"]

            self.log("[*] Network diagnostics...")
            data["network"] = get_network_info()

            self.log("[*] Analyzing processes...")
            data["processes"] = get_top_processes()

            self.log("[*] Calculating health...")
            data["health"] = calculate_health(data["cpu"], data["ram"], data["disk"])

            self.log("[*] Root cause analysis...")
            data["root_cause"] = analyze_root_cause(data)
            data["fix_plan"] = generate_fix_plan(data["root_cause"])

            self.log("[*] Running auto-fixes (if needed)...")
            data["auto_fixes"] = run_auto_fixes(data["root_cause"])

            self.log("[*] Checking history...")
            previous = load_previous_report()
            data["changes"] = compare_reports(data, previous)
            save_report(data)

            self.log("[*] Exporting reports...")
            data["export"] = export_report(data)

            self.log("")
            self._print_report(data)

            export_info = data.get("export", {})
            if export_info.get("html"):
                self.log(f"\nHTML report: {export_info['html']}")
            if export_info.get("json"):
                self.log(f"JSON report: {export_info['json']}")

            self.set_status("Done", self.ok)

        except Exception as e:
            self.log(f"\n[ERROR] {e}")
            self.set_status("Error", self.bad)
        finally:
            self.scan_running = False
            self.btn_scan.configure(state="normal", text="  Run Scan  ")

    def _print_report(self, data):
        system = data["system"]
        cpu = data["cpu"]
        ram = data["ram"]
        disks = data["disk"]
        health = data["health"]
        network = data["network"]
        root_cause = data["root_cause"]
        fix_plan = data["fix_plan"]
        processes = data["processes"]
        changes = data.get("changes", [])
        auto_fixes = data.get("auto_fixes", [])

        lines = []
        lines.append("=" * 54)
        lines.append("         ITOps Assistant  v1.2")
        lines.append("     System Diagnostics & Auto-Fix")
        lines.append("=" * 54)

        lines.append("\nSYSTEM")
        lines.append(f"  Computer : {system.get('computer_name')}")
        lines.append(f"  User     : {system.get('username')}")
        lines.append(f"  OS       : {system.get('os', {}).get('name')} {system.get('os', {}).get('release')}")

        lines.append("\nCPU")
        lines.append(f"  Name     : {cpu.get('name')}")
        lines.append(f"  Cores    : {cpu.get('physical_cores')} / {cpu.get('logical_cores')} threads")
        lines.append(f"  Usage    : {cpu.get('usage_percent')}%")

        lines.append("\nRAM")
        lines.append(f"  Total    : {ram.get('total_gb')} GB")
        lines.append(f"  Free     : {ram.get('available_gb')} GB")
        lines.append(f"  Usage    : {ram.get('usage_percent')}%")

        lines.append("\nDISKS")
        for d in disks:
            lines.append(
                f"  {d['device']}  {d['usage_percent']}% used  "
                f"({d['free_gb']} GB free)  [{d['status']}]"
            )

        lines.append(f"\nHEALTH  {health.get('score')}/100  —  {health.get('status')}")
        if health.get("recommendations"):
            for r in health["recommendations"]:
                lines.append(f"  - {r}")

        lines.append("\nNETWORK")
        lines.append(f"  Adapter  : {network.get('adapter')}")
        lines.append(f"  IP       : {network.get('ip')}")
        lines.append(f"  Gateway  : {network.get('gateway')}")
        lines.append(
            f"  Tests    : Gateway {'OK' if network.get('gateway_ok') else 'FAIL'} | "
            f"DNS {'OK' if network.get('dns_ok') else 'FAIL'} | "
            f"Internet {'OK' if network.get('internet_ok') else 'FAIL'}"
        )
        gw = network.get("gateway_latency") or {}
        inet = network.get("internet_latency") or {}
        if gw.get("avg_ms") is not None:
            lines.append(f"  Latency  : Gateway {gw['avg_ms']:.0f} ms | Internet {inet.get('avg_ms', 'N/A')} ms")
        lines.append(f"  Status   : {network.get('status')}")

        lines.append(f"\nROOT CAUSE  —  {root_cause.get('status')}")
        if root_cause.get("issues"):
            for issue in root_cause["issues"]:
                lines.append(f"  - {issue}")
        else:
            lines.append("  No issues detected")

        if fix_plan:
            lines.append("\nFIX PLAN")
            for fix in fix_plan:
                lines.append(f"  [{fix['priority']}] {fix['issue']}")
                lines.append(f"       → {fix['fix']}")

        if auto_fixes:
            lines.append("\nAUTO FIXES")
            for fix in auto_fixes:
                mark = "OK" if fix.get("success") else "FAIL"
                lines.append(f"  [{mark}] {fix.get('action')}")
                if fix.get("details"):
                    lines.append(f"       {fix['details']}")

        lines.append("\nTOP CPU PROCESSES")
        for p in processes.get("top_cpu", []):
            lines.append(f"  {p['name']:<28} CPU {p['cpu_percent']:>6.1f}%  RAM {p['memory_percent']:>5.2f}%")

        lines.append("\nTOP RAM PROCESSES")
        for p in processes.get("top_ram", []):
            lines.append(f"  {p['name']:<28} RAM {p['memory_percent']:>6.2f}%  CPU {p['cpu_percent']:>5.1f}%")

        if changes:
            lines.append("\nCHANGES SINCE LAST RUN")
            for c in changes:
                lines.append(f"  - {c}")

        self.log("\n".join(lines))

    def open_reports(self):
        reports = os.path.join(get_app_dir(), "reports")
        os.makedirs(reports, exist_ok=True)
        try:
            os.startfile(reports)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open reports folder:\n{e}")


def main():
    app = ITOpsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
