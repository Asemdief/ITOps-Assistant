"""
ITOps Command v1.10.1 — Premium CustomTkinter shell
Layered surfaces · hero posture · accent rails · same modules backend
"""

from __future__ import annotations

import multiprocessing
import os
import sys
import threading
from datetime import datetime
from tkinter import messagebox

try:
    import customtkinter as ctk
except ImportError:
    print("Missing dependency: customtkinter\n  pip install customtkinter")
    sys.exit(1)

APP_VERSION = "1.10.1"
APP_NAME = "ITOps Command"

# Layered graphite (clear depth, not flat)
BG = "#070708"
SIDEBAR = "#0c0c0e"
SURFACE = "#121214"
CARD = "#161618"
ELEVATED = "#1c1c1f"
BORDER = "#2a2a2e"
BORDER_SOFT = "#222226"
FG = "#fafafa"
MUTED = "#a1a1aa"
DIM = "#71717a"
FAINT = "#52525b"
ACCENT = "#22d3ee"
ACCENT_DIM = "#0891b2"
ACCENT_SOFT = "#0e7490"
OK = "#34d399"
WARN = "#fbbf24"
BAD = "#f87171"


def get_app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class AccentCard(ctk.CTkFrame):
    """Card with left color rail."""

    def __init__(self, master, accent: str = ACCENT, **kwargs):
        super().__init__(master, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER, **kwargs)
        self.grid_columnconfigure(1, weight=1)
        rail = ctk.CTkFrame(self, width=3, fg_color=accent, corner_radius=0)
        rail.grid(row=0, column=0, sticky="ns")
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=0, column=1, sticky="nsew", padx=(0, 2), pady=2)


class KPICard(ctk.CTkFrame):
    def __init__(self, master, title: str, accent: str = ACCENT, **kwargs):
        super().__init__(master, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER, **kwargs)
        self.grid_columnconfigure(1, weight=1)
        ctk.CTkFrame(self, width=3, fg_color=accent, corner_radius=0).grid(row=0, column=0, rowspan=3, sticky="ns")
        ctk.CTkLabel(
            self, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color=FAINT, anchor="w"
        ).grid(row=0, column=1, sticky="ew", padx=(14, 14), pady=(14, 0))
        self.value = ctk.CTkLabel(
            self, text="—", font=ctk.CTkFont(size=26, weight="bold"), text_color=FG, anchor="w"
        )
        self.value.grid(row=1, column=1, sticky="ew", padx=(14, 14), pady=(6, 0))
        self.sub = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11), text_color=DIM, anchor="w")
        self.sub.grid(row=2, column=1, sticky="ew", padx=(14, 14), pady=(2, 14))

    def set(self, value: str, sub: str = "", color: str = FG) -> None:
        self.value.configure(text=value, text_color=color)
        self.sub.configure(text=sub)


class KVRow(ctk.CTkFrame):
    def __init__(self, master, key: str, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkLabel(self, text=key, font=ctk.CTkFont(size=12), text_color=DIM, width=100, anchor="w").pack(
            side="left"
        )
        self.val = ctk.CTkLabel(self, text="—", font=ctk.CTkFont(size=12, weight="bold"), text_color=FG, anchor="w")
        self.val.pack(side="left", fill="x", expand=True)

    def set(self, text: str, color: str = FG) -> None:
        self.val.configure(text=str(text), text_color=color)


class SectionLabel(ctk.CTkFrame):
    def __init__(self, master, title: str, badge: str = "", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(size=13, weight="bold"), text_color=FG).pack(side="left")
        if badge:
            ctk.CTkLabel(
                self,
                text=f"  {badge}  ",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=ACCENT,
                fg_color=ELEVATED,
                corner_radius=4,
            ).pack(side="right")


class DiskBar(ctk.CTkFrame):
    def __init__(self, master, device: str, pct: float, free_gb, status: str, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=device, font=ctk.CTkFont(size=12, weight="bold"), text_color=FG).pack(side="left")
        col = OK if pct < 70 else (WARN if pct < 90 else BAD)
        ctk.CTkLabel(
            top,
            text=f"{pct:.0f}% · {free_gb} GB free · {status}",
            font=ctk.CTkFont(size=11),
            text_color=DIM,
        ).pack(side="right")
        bar = ctk.CTkProgressBar(self, height=8, progress_color=col, fg_color=ELEVATED, corner_radius=4)
        bar.pack(fill="x", pady=(8, 0))
        bar.set(max(0.0, min(1.0, pct / 100.0)))


class ITOpsApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title(f"{APP_NAME}  ·  v{APP_VERSION}")
        self.geometry("1520x920")
        self.minsize(1280, 780)
        self.configure(fg_color=BG)

        self.scan_running = False
        self.last_export: dict = {}
        self.last_security: dict = {}
        self.last_data: dict = {}
        self.current_page = "Dashboard"
        self.nav_btns: dict[str, ctk.CTkButton] = {}
        self.kv: dict[str, KVRow] = {}
        self._summary_text = ""

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()
        self._show_dashboard()

    # ─── sidebar ─────────────────────────────────────────────
    def _build_sidebar(self) -> None:
        side = ctk.CTkFrame(self, width=236, fg_color=SIDEBAR, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)

        # Brand block
        brand = ctk.CTkFrame(side, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(28, 8))
        mark = ctk.CTkFrame(brand, width=40, height=40, fg_color=ELEVATED, corner_radius=10, border_width=1, border_color=BORDER)
        mark.pack(side="left")
        mark.pack_propagate(False)
        ctk.CTkLabel(mark, text="◈", font=ctk.CTkFont(size=18), text_color=ACCENT).place(relx=0.5, rely=0.5, anchor="center")
        names = ctk.CTkFrame(brand, fg_color="transparent")
        names.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(names, text="ITOps", font=ctk.CTkFont(size=17, weight="bold"), text_color=FG).pack(anchor="w")
        ctk.CTkLabel(names, text="COMMAND", font=ctk.CTkFont(size=10, weight="bold"), text_color=ACCENT).pack(anchor="w")

        ctk.CTkLabel(
            side, text="ENDPOINT  ·  OPERATIONS", font=ctk.CTkFont(size=9, weight="bold"), text_color=FAINT, anchor="w"
        ).pack(fill="x", padx=22, pady=(4, 18))

        def section(t: str) -> None:
            ctk.CTkLabel(side, text=t, font=ctk.CTkFont(size=9, weight="bold"), text_color=FAINT, anchor="w").pack(
                fill="x", padx=22, pady=(12, 6)
            )

        section("OVERVIEW")
        for key in ("Dashboard", "Endpoint", "Network", "Processes", "Security", "Reports"):
            self._nav_btn(side, key, key)

        section("ACTIONS")
        self._nav_btn(side, "Run Diagnostic", "▶  Run diagnostic", self.start_scan)
        self._nav_btn(side, "Open Reports", "↗  Open reports", self.open_reports)
        self._nav_btn(side, "Open Last HTML", "▤  Last HTML report", self.open_last_html)

        foot = ctk.CTkFrame(side, fg_color=CARD, corner_radius=10, border_width=1, border_color=BORDER)
        foot.pack(side="bottom", fill="x", padx=14, pady=16)
        inner = ctk.CTkFrame(foot, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=12)
        ctk.CTkLabel(inner, text="●  Local agent", font=ctk.CTkFont(size=11), text_color=OK).pack(side="left")
        ctk.CTkLabel(inner, text=f"v{APP_VERSION}", font=ctk.CTkFont(size=10), text_color=FAINT).pack(side="right")

    def _nav_btn(self, parent, key: str, label: str, command=None) -> None:
        btn = ctk.CTkButton(
            parent,
            text=label,
            anchor="w",
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            hover_color=ELEVATED,
            text_color=MUTED,
            height=38,
            corner_radius=8,
            command=command or (lambda k=key: self._navigate(k)),
        )
        btn.pack(fill="x", padx=12, pady=2)
        self.nav_btns[key] = btn

    # ─── main ────────────────────────────────────────────────
    def _build_main(self) -> None:
        self.main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.main, fg_color=BG, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=32, pady=(24, 6))
        header.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(header, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        self.page_title = ctk.CTkLabel(left, text="Dashboard", font=ctk.CTkFont(size=26, weight="bold"), text_color=FG)
        self.page_title.pack(anchor="w")
        self.page_sub = ctk.CTkLabel(
            left, text="Endpoint visibility · diagnostics · remediation", font=ctk.CTkFont(size=12), text_color=DIM
        )
        self.page_sub.pack(anchor="w", pady=(4, 0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")
        self.clock_var = ctk.StringVar(value="")
        ctk.CTkLabel(
            right, textvariable=self.clock_var, font=ctk.CTkFont(family="Consolas", size=12), text_color=FAINT
        ).pack(side="right", padx=(14, 0))
        self.btn_scan = ctk.CTkButton(
            right,
            text="  Run diagnostic  ",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=FG,
            text_color=BG,
            hover_color="#e4e4e7",
            height=40,
            corner_radius=10,
            command=self.start_scan,
        )
        self.btn_scan.pack(side="right", pady=(10, 0))

        self.status_var = ctk.StringVar(value="Ready — local agent online")
        ctk.CTkLabel(header, textvariable=self.status_var, font=ctk.CTkFont(size=11), text_color=DIM).grid(
            row=1, column=0, sticky="w", pady=(12, 0)
        )
        self.progress = ctk.CTkProgressBar(header, height=3, progress_color=ACCENT, fg_color=ELEVATED, corner_radius=2)
        self.progress.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.progress.set(0)
        self._tick_clock()

        self.content = ctk.CTkFrame(self.main, fg_color=BG, corner_radius=0)
        self.content.grid(row=1, column=0, sticky="nsew", padx=32, pady=(8, 24))
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    def _clear_content(self) -> None:
        for w in self.content.winfo_children():
            w.destroy()

    def _show_dashboard(self) -> None:
        self._clear_content()
        root = ctk.CTkFrame(self.content, fg_color=BG)
        root.grid(row=0, column=0, sticky="nsew")
        root.grid_columnconfigure(0, weight=3)
        root.grid_columnconfigure(1, weight=2)
        root.grid_rowconfigure(1, weight=1)

        # KPI row
        kpi = ctk.CTkFrame(root, fg_color="transparent")
        kpi.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        kpi.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.kpi_health = KPICard(kpi, "POSTURE", accent=ACCENT)
        self.kpi_cpu = KPICard(kpi, "CPU LOAD", accent=OK)
        self.kpi_ram = KPICard(kpi, "MEMORY", accent=WARN)
        self.kpi_net = KPICard(kpi, "NETWORK", accent=ACCENT_DIM)
        for i, card in enumerate((self.kpi_health, self.kpi_cpu, self.kpi_ram, self.kpi_net)):
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))

        # LEFT column: host + storage/network
        left = ctk.CTkFrame(root, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)
        left.grid_columnconfigure(1, weight=1)

        # Host card
        host = ctk.CTkFrame(left, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
        host.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        head = ctk.CTkFrame(host, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(14, 6))
        SectionLabel(head, "Host profile", "LIVE").pack(fill="x")

        # hero strip inside host
        hero = ctk.CTkFrame(host, fg_color=ELEVATED, corner_radius=8)
        hero.pack(fill="x", padx=16, pady=(4, 10))
        self.hero_host = ctk.CTkLabel(
            hero, text="Awaiting diagnostic", font=ctk.CTkFont(size=15, weight="bold"), text_color=FG, anchor="w"
        )
        self.hero_host.pack(fill="x", padx=14, pady=(12, 0))
        self.hero_os = ctk.CTkLabel(hero, text="Run diagnostic to populate endpoint data", font=ctk.CTkFont(size=11), text_color=DIM, anchor="w")
        self.hero_os.pack(fill="x", padx=14, pady=(2, 12))

        grid = ctk.CTkFrame(host, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 14))
        grid.grid_columnconfigure((0, 1), weight=1)
        pairs = (
            ("host", "Hostname"),
            ("user", "User"),
            ("os", "Operating system"),
            ("score", "Posture score"),
            ("cpu_name", "CPU model"),
            ("cpu_load", "CPU load"),
            ("ram_used", "RAM used"),
            ("ram_free", "RAM free"),
        )
        for i, (key, label) in enumerate(pairs):
            cell = ctk.CTkFrame(grid, fg_color="transparent")
            cell.grid(row=i // 2, column=i % 2, sticky="ew", padx=(0 if i % 2 == 0 else 12, 0), pady=4)
            row = KVRow(cell, label)
            row.pack(fill="x")
            self.kv[key] = row

        # Storage
        stor = ctk.CTkFrame(left, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
        stor.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        sh = ctk.CTkFrame(stor, fg_color="transparent")
        sh.pack(fill="x", padx=16, pady=(14, 8))
        SectionLabel(sh, "Storage", "DISKS").pack(fill="x")
        self.disk_box = ctk.CTkFrame(stor, fg_color="transparent")
        self.disk_box.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        ctk.CTkLabel(self.disk_box, text="No disk data yet", font=ctk.CTkFont(size=12), text_color=DIM).pack(anchor="w")

        # Network
        net = ctk.CTkFrame(left, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
        net.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        nh = ctk.CTkFrame(net, fg_color="transparent")
        nh.pack(fill="x", padx=16, pady=(14, 8))
        SectionLabel(nh, "Network path", "LINK").pack(fill="x")
        for key, label in (
            ("adapter", "Adapter"),
            ("ip", "IP address"),
            ("gateway", "Gateway"),
            ("net_status", "Status"),
        ):
            row = KVRow(net, label)
            row.pack(fill="x", padx=16, pady=4)
            self.kv[key] = row
        ctk.CTkFrame(net, height=8, fg_color="transparent").pack()

        # RIGHT column
        right = ctk.CTkFrame(root, fg_color="transparent")
        right.grid(row=1, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)

        # Posture hero
        posture = ctk.CTkFrame(right, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
        posture.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ph = ctk.CTkFrame(posture, fg_color="transparent")
        ph.pack(fill="x", padx=16, pady=(14, 6))
        SectionLabel(ph, "Posture", "SCORE").pack(fill="x")
        self.score_big = ctk.CTkLabel(
            posture, text="—", font=ctk.CTkFont(size=48, weight="bold"), text_color=FG
        )
        self.score_big.pack(anchor="w", padx=16, pady=(4, 0))
        self.score_status = ctk.CTkLabel(
            posture, text="No diagnostic yet", font=ctk.CTkFont(size=13, weight="bold"), text_color=DIM
        )
        self.score_status.pack(anchor="w", padx=16, pady=(0, 4))
        self.score_hint = ctk.CTkLabel(
            posture,
            text="Score from CPU, memory and storage pressure.",
            font=ctk.CTkFont(size=11),
            text_color=FAINT,
            wraplength=280,
            justify="left",
        )
        self.score_hint.pack(anchor="w", padx=16, pady=(0, 16))

        # Findings
        find = ctk.CTkFrame(right, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
        find.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        fh = ctk.CTkFrame(find, fg_color="transparent")
        fh.pack(fill="x", padx=16, pady=(14, 8))
        SectionLabel(fh, "Findings", "RCA").pack(fill="x")
        self.findings_box = ctk.CTkScrollableFrame(find, fg_color="transparent", height=160)
        self.findings_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        ctk.CTkLabel(self.findings_box, text="No findings yet", font=ctk.CTkFont(size=12), text_color=DIM).pack(
            anchor="w"
        )

        # Activity
        act = ctk.CTkFrame(right, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
        act.grid(row=2, column=0, sticky="ew")
        ah = ctk.CTkFrame(act, fg_color="transparent")
        ah.pack(fill="x", padx=16, pady=(14, 8))
        SectionLabel(ah, "Activity", "PIPELINE").pack(fill="x")
        self.log_box = ctk.CTkTextbox(
            act,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=BG,
            text_color=DIM,
            corner_radius=8,
            height=130,
            border_width=0,
        )
        self.log_box.pack(fill="x", padx=12, pady=(0, 12))
        self.log_box.insert("end", "Local console online.\nPipeline idle.\n")
        self.log_box.configure(state="disabled")


    def _show_security_page(self) -> None:
        self._clear_content()
        panel = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
        panel.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(
            panel, text="Security posture", font=ctk.CTkFont(size=16, weight="bold"), text_color=FG
        ).pack(anchor="w", padx=18, pady=(16, 6))
        sec = self.last_security or {}
        if not sec:
            ctk.CTkLabel(
                panel,
                text="No security scan yet. Run diagnostic to collect posture checks.",
                font=ctk.CTkFont(size=12),
                text_color=DIM,
            ).pack(anchor="w", padx=18, pady=(8, 16))
            return
        score = sec.get("score")
        grade = sec.get("grade", "—")
        cov = (sec.get("coverage") or {}).get("percent", "—")
        color = OK if (score or 0) >= 85 else (WARN if (score or 0) >= 60 else BAD)
        head = ctk.CTkFrame(panel, fg_color=ELEVATED, corner_radius=8)
        head.pack(fill="x", padx=16, pady=(4, 10))
        ctk.CTkLabel(
            head,
            text=f"Score  {score if score is not None else '—'}   ·   Grade  {grade}   ·   Coverage  {cov}%",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=color,
        ).pack(anchor="w", padx=14, pady=12)
        box = ctk.CTkTextbox(
            panel, font=ctk.CTkFont(family="Consolas", size=12), fg_color=BG, text_color=MUTED, corner_radius=8
        )
        box.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        try:
            from modules.security import format_text
            box.insert("end", format_text(sec))
        except Exception:
            lines = [f"{f.get('id')}  [{f.get('status')}]  {f.get('title')} — {f.get('actual')}"
                     for f in (sec.get('findings') or [])[:40]]
            box.insert("end", "\n".join(lines) or "No findings.")
        box.configure(state="disabled")

    def _show_text_page(self, title: str, body: str) -> None:
        self._clear_content()
        panel = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
        panel.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(panel, text=title, font=ctk.CTkFont(size=16, weight="bold"), text_color=FG).pack(
            anchor="w", padx=18, pady=(16, 8)
        )
        box = ctk.CTkTextbox(panel, font=ctk.CTkFont(family="Consolas", size=12), fg_color=BG, text_color=MUTED, corner_radius=8)
        box.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        box.insert("end", body or "Run a diagnostic first.")
        box.configure(state="disabled")

    def _show_reports_page(self) -> None:
        self._clear_content()
        panel = ctk.CTkFrame(self.content, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
        panel.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(panel, text="Reports", font=ctk.CTkFont(size=16, weight="bold"), text_color=FG).pack(
            anchor="w", padx=18, pady=(16, 8)
        )
        actions = ctk.CTkFrame(panel, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(0, 10))
        ctk.CTkButton(
            actions, text="Open last report", command=self.open_last_html, fg_color=ELEVATED, hover_color=BORDER, height=36, corner_radius=8
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions, text="Open folder", command=self.open_reports, fg_color=ELEVATED, hover_color=BORDER, height=36, corner_radius=8
        ).pack(side="left")
        path = (self.last_export or {}).get("html") or "No report yet. Run a diagnostic."
        box = ctk.CTkTextbox(panel, font=ctk.CTkFont(family="Consolas", size=12), fg_color=BG, text_color=MUTED, height=140, corner_radius=8)
        box.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        box.insert("end", str(path))
        box.configure(state="disabled")

    def _navigate(self, name: str) -> None:
        self.current_page = name
        for key, btn in self.nav_btns.items():
            if key in ("Run Diagnostic", "Open Reports", "Open Last HTML"):
                continue
            active = key == name
            btn.configure(
                fg_color=ELEVATED if active else "transparent",
                text_color=FG if active else MUTED,
                font=ctk.CTkFont(size=13, weight="bold" if active else "normal"),
            )
        titles = {
            "Dashboard": ("Dashboard", "Endpoint visibility · diagnostics · remediation"),
            "Endpoint": ("Endpoint", "Host and resource detail"),
            "Network": ("Network", "Path and connectivity"),
            "Processes": ("Processes", "CPU and memory pressure"),
            "Security": ("Security", "Posture checks · Defender · hardening"),
            "Reports": ("Reports", "Local HTML artifacts"),
        }
        t, s = titles.get(name, (name, ""))
        self.page_title.configure(text=t)
        self.page_sub.configure(text=s)
        if name == "Dashboard":
            self._show_dashboard()
            if self.last_data:
                self._fill_dashboard(self.last_data)
            self.set_status("Ready — local agent online")
            return
        if name == "Reports":
            self._show_reports_page()
            return
        if name == "Security":
            self._show_security_page()
            return
        if name == "Network":
            self._show_network_page()
            return
        if name == "Processes":
            self._show_processes_page()
            return
        # Endpoint
        self._show_endpoint_page()

    def _tick_clock(self) -> None:
        self.clock_var.set(datetime.now().strftime("%Y-%m-%d  %H:%M"))
        self.after(1000, self._tick_clock)

    def set_progress(self, ratio: float) -> None:
        self.after(0, lambda: self.progress.set(max(0.0, min(1.0, ratio))))

    def set_status(self, text: str) -> None:
        self.after(0, lambda: self.status_var.set(text))

    def log(self, msg: str) -> None:
        def _() -> None:
            if not hasattr(self, "log_box") or not self.log_box.winfo_exists():
                return
            self.log_box.configure(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self.after(0, _)

    def set_summary(self, text: str) -> None:
        self._summary_text = text

    def update_cards(self, health: dict, cpu: dict, ram: dict, network: dict) -> None:
        def _() -> None:
            if not hasattr(self, "kpi_health"):
                return
            try:
                if not self.kpi_health.winfo_exists():
                    return
            except Exception:
                return
            score = int(health.get("score", 0) or 0)
            status = str(health.get("status", "—"))
            color = OK if score >= 85 else (WARN if score >= 60 else BAD)
            self.kpi_health.set(f"{score}/100", status.upper(), color)
            if hasattr(self, "score_big"):
                try:
                    self.score_big.configure(text=str(score), text_color=color)
                    self.score_status.configure(text=status.upper(), text_color=color)
                except Exception:
                    pass
            cu = float(cpu.get("usage_percent") or 0)
            self.kpi_cpu.set(
                f"{cu:.1f}%",
                str(cpu.get("name", "CPU"))[:34],
                OK if cu < 70 else (WARN if cu < 90 else BAD),
            )
            ru = float(ram.get("usage_percent") or 0)
            self.kpi_ram.set(
                f"{ru:.1f}%",
                f"{ram.get('available_gb', 0)} GB free",
                OK if ru < 75 else (WARN if ru < 90 else BAD),
            )
            net_status = str(network.get("status", "—"))
            online = "OK" in net_status.upper()
            self.kpi_net.set("ONLINE" if online else "DEGRADED", net_status, OK if online else BAD)

        self.after(0, _)

    def _fill_dashboard(self, data: dict) -> None:
        """Synchronously paint dashboard widgets from data (must run on UI thread)."""
        if not hasattr(self, "kv") or "host" not in self.kv:
            return
        s = data.get("system") or {}
        c = data.get("cpu") or {}
        r = data.get("ram") or {}
        h = data.get("health") or {}
        n = data.get("network") or {}
        osd = s.get("os") or {}
        score = h.get("score", "—")

        if hasattr(self, "hero_host"):
            try:
                self.hero_host.configure(text=f"{s.get('computer_name', '—')}  /  {s.get('username', '')}")
                self.hero_os.configure(text=f"{osd.get('name', '')} {osd.get('release', '')}".strip() or "—")
            except Exception:
                pass

        def set_kv(key: str, val, color: str = FG) -> None:
            row = self.kv.get(key)
            if row:
                try:
                    row.set(val, color)
                except Exception:
                    pass

        set_kv("host", s.get("computer_name", "—"))
        set_kv("user", s.get("username", "—"))
        set_kv("os", f"{osd.get('name', '')} {osd.get('release', '')}".strip() or "—")
        set_kv("score", f"{score}/100  ·  {h.get('status', '')}")
        set_kv("cpu_name", str(c.get("name", "—"))[:42])
        set_kv("cpu_load", f"{c.get('usage_percent', 0)}%")
        set_kv("ram_used", f"{r.get('usage_percent', 0)}%")
        set_kv("ram_free", f"{r.get('available_gb', 0)} GB / {r.get('total_gb', 0)} GB")
        set_kv("adapter", n.get("adapter", "—"))
        set_kv("ip", n.get("ip", "—"))
        set_kv("gateway", n.get("gateway", "—"))
        st = str(n.get("status", "—"))
        set_kv("net_status", st, OK if "OK" in st.upper() else BAD)

        if hasattr(self, "disk_box"):
            for w in self.disk_box.winfo_children():
                w.destroy()
            disks = data.get("disk") or []
            if not disks:
                ctk.CTkLabel(self.disk_box, text="No disk data", font=ctk.CTkFont(size=12), text_color=DIM).pack(anchor="w")
            else:
                for d in disks:
                    DiskBar(
                        self.disk_box,
                        str(d.get("device", "?")),
                        float(d.get("usage_percent") or 0),
                        d.get("free_gb", "—"),
                        str(d.get("status", "")),
                    ).pack(fill="x", pady=6)

        if hasattr(self, "findings_box"):
            for w in self.findings_box.winfo_children():
                w.destroy()
            rc = data.get("root_cause") or {}
            issues = rc.get("issues") or []
            if not issues:
                chip = ctk.CTkFrame(self.findings_box, fg_color=ELEVATED, corner_radius=8)
                chip.pack(fill="x", pady=4)
                ctk.CTkLabel(
                    chip, text="  ✓  No issues — baseline healthy", font=ctk.CTkFont(size=12), text_color=OK, anchor="w"
                ).pack(fill="x", padx=8, pady=8)
            else:
                for i in issues:
                    chip = ctk.CTkFrame(self.findings_box, fg_color=ELEVATED, corner_radius=8)
                    chip.pack(fill="x", pady=3)
                    ctk.CTkLabel(
                        chip, text=f"  !  {i}", font=ctk.CTkFont(size=12), text_color=FG, anchor="w", wraplength=300, justify="left"
                    ).pack(fill="x", padx=8, pady=8)
            fixes = data.get("auto_fixes") or []
            if fixes:
                ctk.CTkLabel(
                    self.findings_box, text="Remediation", font=ctk.CTkFont(size=11, weight="bold"), text_color=FAINT
                ).pack(anchor="w", pady=(12, 4))
                for f in fixes[:8]:
                    mark = "OK" if f.get("success") else "SKIP"
                    col = OK if f.get("success") else DIM
                    ctk.CTkLabel(
                        self.findings_box,
                        text=f"  [{mark}]  {f.get('action', '')}",
                        font=ctk.CTkFont(size=11),
                        text_color=col,
                        anchor="w",
                        wraplength=300,
                        justify="left",
                    ).pack(anchor="w", pady=1)

        self.update_cards(data.get("health") or {}, data.get("cpu") or {}, data.get("ram") or {}, data.get("network") or {})

    def _apply_dashboard(self, data: dict) -> None:
        self.last_data = data
        def _() -> None:
            self.current_page = "Dashboard"
            # refresh nav highlight
            for key, btn in self.nav_btns.items():
                if key in ("Run Diagnostic", "Open Reports", "Open Last HTML"):
                    continue
                active = key == "Dashboard"
                btn.configure(
                    fg_color=ELEVATED if active else "transparent",
                    text_color=FG if active else MUTED,
                    font=ctk.CTkFont(size=13, weight="bold" if active else "normal"),
                )
            self.page_title.configure(text="Dashboard")
            self.page_sub.configure(text="Endpoint visibility · diagnostics · remediation")
            self._show_dashboard()
            self._fill_dashboard(data)
        self.after(0, _)

    def _show_network_page(self) -> None:
        n = (self.last_data or {}).get("network") or {}
        if not n:
            self._show_text_page("Network detail", "Run a diagnostic first.")
            return
        gw_lat = n.get("gateway_latency") or {}
        inet_lat = n.get("internet_latency") or {}
        lines = [
            f"Adapter        {n.get('adapter', '—')}",
            f"IP address     {n.get('ip', '—')}",
            f"Netmask        {n.get('netmask', '—')}",
            f"MAC            {n.get('mac', '—')}",
            f"Gateway        {n.get('gateway', '—')}",
            f"Gateway OK     {n.get('gateway_ok')}",
            f"DNS OK         {n.get('dns_ok')}",
            f"Internet OK    {n.get('internet_ok')}",
            f"Status         {n.get('status', '—')}",
            f"Gateway latency  {gw_lat.get('avg_ms')} ms  (loss {gw_lat.get('loss_percent')}%)",
            f"Internet latency {inet_lat.get('avg_ms')} ms  (loss {inet_lat.get('loss_percent')}%)  method={inet_lat.get('method')}",
        ]
        self._show_text_page("Network detail", "\n".join(lines))

    def _show_processes_page(self) -> None:
        procs = (self.last_data or {}).get("processes") or {}
        if not procs:
            self._show_text_page("Process detail", "Run a diagnostic first.")
            return
        lines = ["TOP CPU"]
        for p in procs.get("top_cpu") or []:
            lines.append(f"  {str(p.get('name','?'))[:28]:<28} {float(p.get('cpu_percent') or 0):>6.1f}%")
        lines.append("")
        lines.append("TOP MEMORY")
        for p in procs.get("top_ram") or []:
            lines.append(f"  {str(p.get('name','?'))[:28]:<28} {float(p.get('memory_percent') or 0):>6.2f}%")
        self._show_text_page("Process detail", "\n".join(lines))

    def _show_endpoint_page(self) -> None:
        data = self.last_data or {}
        if not data:
            self._show_text_page("Endpoint detail", "Run a diagnostic first.")
            return
        # Prefer full summary if present
        text = self._summary_text or self._format_summary(data)
        self._show_text_page("Endpoint detail", text)

    def start_scan(self) -> None:
        if self.scan_running:
            return
        self.scan_running = True
        self.btn_scan.configure(state="disabled", text="  Scanning…  ")
        if self.current_page != "Dashboard":
            self._navigate("Dashboard")
        self.set_progress(0.05)
        self.set_status("Pipeline active — collecting endpoint telemetry")
        self.log("════════ DIAGNOSTIC INIT ════════")
        threading.Thread(target=self._run_scan, daemon=True).start()

    def _run_scan(self) -> None:
        try:
            from modules.inventory import get_inventory
            from modules.network import get_network_info
            from modules.processes import get_top_processes
            from modules.health import calculate_health
            from modules.root_cause import analyze_root_cause
            from modules.fix_plan import generate_fix_plan
            from modules.fix_engine import run_auto_fixes
            from modules.history import load_previous_report, compare_reports, save_report
            from modules.export import export_report

            data: dict = {}
            self.log("[1/9] inventory / host profile")
            self.set_progress(0.12)
            inv = get_inventory()
            data["system"] = inv["system"]
            data["cpu"] = inv["cpu"]
            data["ram"] = inv["ram"]
            data["disk"] = inv["disk"]

            self.log("[2/9] network path + latency probes")
            self.set_progress(0.28)
            data["network"] = get_network_info()

            self.log("[3/9] process pressure map")
            self.set_progress(0.42)
            data["processes"] = get_top_processes()

            self.log("[4/9] posture score")
            self.set_progress(0.55)
            data["health"] = calculate_health(data["cpu"], data["ram"], data["disk"])

            self.log("[5/9] root-cause matrix")
            self.set_progress(0.65)
            data["root_cause"] = analyze_root_cause(data)
            data["fix_plan"] = generate_fix_plan(data["root_cause"])

            self.log("[6/9] silent remediation playbooks")
            self.set_progress(0.78)
            data["auto_fixes"] = run_auto_fixes(data["root_cause"])

            self.log("[7/9] security posture scan")
            self.set_progress(0.82)
            try:
                from modules.security import run_security_scan

                def _sec_progress(finding, i, n):
                    self.set_status(f"Security check {i}/{n}: {finding.get('id', '')}")

                data["security"] = run_security_scan(progress=_sec_progress)
                self.last_security = data["security"]
                sc = data["security"].get("score")
                self.log(f"      security score={sc} grade={data['security'].get('grade')}")
            except Exception as se:
                data["security"] = {"error": str(se), "score": None, "findings": []}
                self.last_security = data["security"]
                self.log(f"      security scan skipped: {se}")

            self.log("[8/9] delta vs last session")
            self.set_progress(0.90)
            prev = load_previous_report()
            data["changes"] = compare_reports(data, prev)
            save_report(data)

            self.log("[9/9] build premium HTML report")
            self.set_progress(0.96)
            data["export"] = export_report(data)
            self.last_export = data.get("export") or {}

            self.last_data = data
            self.update_cards(data["health"], data["cpu"], data["ram"], data["network"])
            self.set_summary(self._format_summary(data))
            self._apply_dashboard(data)
            self.set_progress(1.0)
            self.log("════════ DIAGNOSTIC COMPLETE ════════")
            if self.last_export.get("html"):
                self.log(f"artifact → {self.last_export['html']}")
            self.set_status("Diagnostic complete — endpoint report ready")
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.set_status("Pipeline error — inspect Activity log")
        finally:
            self.scan_running = False
            self.after(0, lambda: self.btn_scan.configure(state="normal", text="  Run diagnostic  "))

    def _format_summary(self, data: dict) -> str:
        s, c, r, h, n, rc = (
            data["system"], data["cpu"], data["ram"], data["health"], data["network"], data["root_cause"]
        )
        score = h.get("score", 0)
        posture = "HEALTHY" if score >= 90 else ("ATTENTION" if score >= 60 else "CRITICAL")
        lines = [
            f"ENDPOINT POSTURE  {posture}",
            f"HOST  {s.get('computer_name')} / {s.get('username')}",
            f"OS  {s.get('os', {}).get('name')} {s.get('os', {}).get('release')}",
            f"SCORE  {score}/100 — {h.get('status')}",
            f"CPU  {c.get('usage_percent')}% · {c.get('name')}",
            f"MEMORY  {r.get('usage_percent')}% · {r.get('available_gb')} GB free",
            "",
            "STORAGE",
        ]
        for d in data.get("disk") or []:
            lines.append(f"  {d.get('device')}  {d.get('usage_percent')}%  [{d.get('status')}]")
        lines += [
            "",
            "NETWORK",
            f"  {n.get('adapter')} · {n.get('ip')} · {n.get('status')}",
            f"ROOT CAUSE  {rc.get('status')}",
        ]
        for i in rc.get("issues") or []:
            lines.append(f"  · {i}")
        lines += ["", "TOP CPU"]
        for p in (data.get("processes") or {}).get("top_cpu", [])[:5]:
            lines.append(f"  {str(p.get('name','?'))[:26]:<26} {p.get('cpu_percent',0):>6.1f}%")
        lines += ["", "TOP MEMORY"]
        for p in (data.get("processes") or {}).get("top_ram", [])[:5]:
            lines.append(f"  {str(p.get('name','?'))[:26]:<26} {p.get('memory_percent',0):>6.2f}%")
        return "\n".join(lines)

    def open_reports(self) -> None:
        path = os.path.join(get_app_dir(), "reports")
        os.makedirs(path, exist_ok=True)
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("Reports", str(e))

    def open_last_html(self) -> None:
        html = (self.last_export or {}).get("html")
        if not html or not os.path.isfile(html):
            reports = os.path.join(get_app_dir(), "reports")
            if os.path.isdir(reports):
                htmls = sorted(
                    [os.path.join(reports, f) for f in os.listdir(reports) if f.endswith(".html")],
                    key=os.path.getmtime,
                    reverse=True,
                )
                html = htmls[0] if htmls else None
        if not html:
            messagebox.showinfo("Reports", "No HTML report yet. Run a diagnostic first.")
            return
        try:
            os.startfile(html)
        except Exception as e:
            messagebox.showerror("HTML Report", str(e))


def main() -> None:
    app = ITOpsApp()
    app.mainloop()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
