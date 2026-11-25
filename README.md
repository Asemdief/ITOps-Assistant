# ITOps Command

**Windows endpoint diagnostics and silent remediation — built for IT support.**

Double-click. No console flash. Structured findings instead of raw numbers. Local HTML/JSON reports only.

```text
Instead of:   RAM 87%  ·  Disk C: 91%  ·  Ping failed
You get:      High memory pressure · Critical free space on C:
              Top consumers · prioritised fix plan · safe auto-actions
              Internet OK (DNS/TCP path verified — not ICMP-only)
```

**Current release:** v1.9.1 (GUI) · Product name **ITOps Command** · Repo **ITOps-Assistant**

---

## Who it’s for

- Helpdesk / L1–L2 support
- System administrators
- MSP technicians
- Small IT teams that need fast, consistent machine checks

---

## Features

### Diagnostics

| Area | What you get |
|------|----------------|
| **Inventory** | Host, user, OS, CPU, RAM, disk partitions + status |
| **Network** | Active adapter (virtual filtered), gateway, DNS, internet path, latency |
| **Processes** | Top CPU / RAM with system noise filtered |
| **Health** | Score 0–100 + posture status |
| **Root cause** | Human-readable issues + suggestions |
| **History** | Delta vs last successful run |
| **Export** | Premium HTML + JSON next to the app |

### Silent remediation (safe defaults)

- Clean user TEMP (skips locked/recent files)
- Flush DNS / clear DNS client cache
- Empty Recycle Bin when disk pressure is detected
- No visible `cmd.exe` / PowerShell windows (`modules/win_silent.py`)

### Security posture (read-only scan + opt-in fixes)

- `modules/security.py` — multi-check scan, severity-weighted score, coverage
- `modules/security_fix.py` — dry-run by default, journal, rollback
- `modules/registry_io.py` — winreg helpers
- Fixes are **never** applied without explicit opt-in

### Network HARD RULE

DNS resolution **or** TCP/HTTPS success ⇒ **Internet OK**.  
ICMP ping failure alone does **not** mark the machine offline (common on restricted networks).

---

## UX

- **CustomTkinter** dark graphite shell (quiet SOC style)
- Sidebar: Dashboard, Endpoint, Network, Processes, Reports
- Primary action: **Run diagnostic**
- KPIs, host/storage panels, findings list — not a terminal dump

---

## Requirements

- Windows 10 / 11
- Python 3.10+ (for source runs)
- Dependencies:

```text
psutil>=5.9.0
customtkinter>=5.2.0
```

---

## Quick start (source)

```bash
git clone https://github.com/Asemdief/ITOps-Assistant.git
cd ITOps-Assistant
pip install -r requirements.txt
python gui.py
```

Windows helpers (no console):

```bat
run_gui.vbs
```

or:

```bat
run_gui.bat
```

---

## Build standalone `.exe`

```bat
build_exe.bat
```

Produces:

```text
dist\ITOps-Assistant.exe
```

Flags used: `--onefile --windowed --noconsole` (+ icon / version info when present).

> Run as Administrator when you need stronger remediation or HKLM-related security fixes.

---

## Project layout

```text
ITOps-Assistant/
├── gui.py                 # Main entry — CustomTkinter UI + scan orchestration
├── main.py                # Optional CLI-oriented entry
├── modules/
│   ├── inventory.py       # System / CPU / RAM / disks
│   ├── network.py         # Adapters, gateway, DNS, internet probes (HARD RULE)
│   ├── processes.py       # Top CPU / RAM
│   ├── health.py          # Score 0–100
│   ├── root_cause.py      # Findings from telemetry
│   ├── fix_plan.py        # Prioritised suggestions
│   ├── fix_engine.py      # Silent auto-fixes
│   ├── history.py         # Previous run + deltas
│   ├── export.py          # HTML + JSON reports
│   ├── paths.py           # App dir (source + frozen exe)
│   ├── win_silent.py      # CREATE_NO_WINDOW helpers
│   ├── security.py        # Security posture scan (read-only)
│   ├── security_fix.py    # Opt-in fixes + journal / rollback
│   ├── registry_io.py     # Registry access layer
│   └── config_loader.py   # Optional config
├── docs/
│   └── SECURITY_MODULE.md
├── tests/
│   └── test_security.py
├── build_exe.bat
├── run_gui.bat / run_gui.vbs
├── version_info.txt
├── requirements.txt
└── README.md
```

### Scan pipeline

1. Inventory  
2. Network path + probes  
3. Process pressure  
4. Health score  
5. Root-cause matrix  
6. Silent remediation (when applicable)  
7. History delta  
8. Export HTML + JSON  

GUI runs the pipeline on a **background thread**; UI updates stay on the main thread.

---

## Product rules (non-negotiable)

1. **No black console flash** — all system commands via silent helpers  
2. **Double-click product** — windowed exe for end users  
3. **Modular backend** — logic in `modules/`; GUI only orchestrates and displays  
4. **Local reports only** — no cloud egress by default  
5. **Honest network status** — DNS/TCP path, not ICMP-only  

---

## Tests

```bash
python -m unittest tests.test_security -v
```

---

## Roadmap (high level)

| Phase | Focus | Status |
|-------|--------|--------|
| Core diagnostics + auto-fix + export | Local MVP | Done |
| Packaging (windowed exe) | Distribution | Done |
| CustomTkinter commercial UI | Sellable shell | Done (v1.9.x) |
| Security posture tab | Read-only + opt-in fixes | Present in tree |
| Agent + central dashboard | Multi-device / MSP | Planned |
| Installer + licensing | Commercial packaging | Planned |

---

## Environments

Developed and tested across:

| | Home | Work |
|--|------|------|
| Example host | ASEM-CORE | Asem-CORE |
| OS | Windows 10 | Windows 11 |

No drive-letter hardcoding in core logic.

---

## License / commercial use

Active development under **ITOps Command**.  
Contact the maintainer for commercial licensing or custom builds.

---

## Maintainer

**Asem Dief** · [github.com/Asemdief](https://github.com/Asemdief)

Repository: [github.com/Asemdief/ITOps-Assistant](https://github.com/Asemdief/ITOps-Assistant)

---

**Status:** Active development · Windows-first · Built for operators, not demos.
