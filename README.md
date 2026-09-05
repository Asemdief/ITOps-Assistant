# 🚀 ITOps Assistant

**Intelligent IT Support automation for Windows endpoints.**

ITOps Assistant turns raw system data into actionable diagnostics, prioritized fix plans, and safe automatic remediation — so L1 / Helpdesk engineers spend less time collecting information and more time solving real problems.

```text
Instead of:   RAM Usage: 87%
You get:      High RAM usage detected
              Top consumers: chrome.exe (1.8 GB), Teams (920 MB)
              Suggested action: Close unused browser tabs or restart Teams
              Auto-fix available: Clean TEMP + Empty Recycle Bin
```

---

## ✨ Current Features

### 🖥 Inventory Collection
- System info (hostname, user, OS)
- CPU name, cores, live usage
- RAM total / available / usage %
- Disk partitions with clear status levels (Healthy → Critical)

### 🌐 Network Diagnostics
- Active adapter detection (filters virtual adapters)
- Gateway reachability
- DNS resolution check
- Internet connectivity test
- Basic latency measurement

### 📊 Process Analysis
- Top processes by CPU and by RAM
- Filters noisy system processes
- Flags high consumers automatically

### ❤️ Device Health Scoring
- Overall health score (0–100)
- Status classification: Excellent / Good / Warning / Critical
- Risk indicators based on CPU, RAM, and disk thresholds

### 🧠 Root Cause Analysis
- Correlates CPU, RAM, Disk, and Network signals
- Human-readable issue list
- Prioritized suggestions

### 🛠 Fix Planning + Safe Auto-Fixes
- Generates prioritized remediation plan
- Safe automatic actions when issues are detected:
  - Flush DNS cache
  - Restart DNS Client service
  - Clean user TEMP folder (skips locked/recent files)
  - Empty Recycle Bin
  - Trigger Disk Cleanup (silent mode)

### 📜 History & Change Tracking
- Saves last report
- Compares current run vs previous run
- Highlights what changed

### 📄 Report Export
- Clean terminal report
- JSON export
- HTML report (ready to attach to tickets or send to clients)

---

## 🎯 Target Users

- IT Support / Helpdesk (L1–L2)
- System Administrators
- MSP technicians
- Small & medium business IT teams

---

## ⚡ Tech Stack

| Component        | Technology                          |
|------------------|-------------------------------------|
| Language         | Python 3.10+                        |
| System metrics   | `psutil`, `py-cpuinfo`              |
| Network checks   | Built-in + subprocess (Windows)     |
| Reports          | JSON + HTML                         |
| Platform         | Windows (primary)                   |

---

## 🚀 Quick Start

### 1. Clone
```bash
git clone https://github.com/Asemdief/ITOps-Assistant.git
cd ITOps-Assistant
```

### 2. Install dependencies
```bash
pip install psutil py-cpuinfo
```

### 3. Run
```bash
python main.py
```

> Some auto-fixes (DNS Client restart, Disk Cleanup, Recycle Bin) work better when run as Administrator.

---

## 📁 Project Structure

```text
ITOps-Assistant/
├── main.py                  # Entry point – orchestrates the full pipeline
├── modules/
│   ├── inventory.py         # System / CPU / RAM collection
│   ├── disk.py              # Disk usage + status
│   ├── network.py           # Adapter, gateway, DNS, internet, latency
│   ├── processes.py         # Top CPU / RAM processes
│   ├── health.py            # Health score engine
│   ├── root_cause.py        # Issue detection + suggestions
│   ├── fix_plan.py          # Prioritized remediation plan
│   ├── fix_engine.py        # Safe auto-fix actions
│   ├── history.py           # Previous report + change detection
│   ├── export.py            # JSON + HTML report export
│   └── formatter.py         # Terminal output formatting
├── .gitignore
├── .gitattributes
└── README.md
```

---

## 🗺 Roadmap

### ✅ Version 0.1 (Current)
- [x] Inventory collection
- [x] Health scoring
- [x] Network diagnostics
- [x] Process analysis
- [x] Root cause analysis
- [x] Fix planning
- [x] Safe auto-fixes
- [x] History comparison
- [x] JSON + HTML export

### 🔄 Version 0.2 (Next)
- [ ] Stronger process → root-cause correlation
- [ ] Startup programs analyzer
- [ ] Windows services health check
- [ ] Event Viewer quick scan (critical errors)
- [ ] Windows Update status check

### 🚀 Version 0.3
- [ ] One-click / approved remote fixes
- [ ] Configurable thresholds
- [ ] Better disk cleanup profiles
- [ ] Export to PDF

### 🏗 Version 1.0 (Product)
- [ ] Lightweight agent + central dashboard
- [ ] Multi-device inventory
- [ ] Scheduled scans
- [ ] Ticketing integrations (webhook / basic)
- [ ] Simple licensing

---

## ⚠️ Notes & Limitations

- Currently **Windows-focused** (uses `ipconfig`, `net`, PowerShell, `cleanmgr`).
- Auto-fixes are intentionally conservative (safe-by-default).
- Some actions require Administrator privileges.
- Virtual network adapters are filtered to reduce noise.
- This is an active MVP — expect rapid iteration.

---

## 📈 Mission

Reduce repetitive IT support work.  
Give engineers clear answers instead of raw numbers.  
Move from “what is the usage?” to “what should I do next?”.

---

## 📄 License

This project is currently under active development.  
License will be added in a future release.

---

**Status:** Active Development 🚧  
**Maintainer:** [Asemdief](https://github.com/Asemdief)
