"""Premium HTML + JSON export — ITOps Command SOC look."""

from __future__ import annotations

import json
import os
from datetime import datetime
from html import escape

from modules.paths import get_app_dir


def _get_export_dir() -> str:
    path = os.path.join(get_app_dir(), "reports")
    os.makedirs(path, exist_ok=True)
    return path


def export_json(data: dict) -> str | None:
    reports_dir = _get_export_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    computer = str(data.get("system", {}).get("computer_name", "unknown")).replace(" ", "_")
    path = os.path.join(reports_dir, f"report_{computer}_{ts}.json")
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.6.2",
        "product": "ITOps Command",
        "system": data.get("system"),
        "cpu": data.get("cpu"),
        "ram": data.get("ram"),
        "disk": data.get("disk"),
        "network": data.get("network"),
        "health": data.get("health"),
        "root_cause": data.get("root_cause"),
        "fix_plan": data.get("fix_plan"),
        "auto_fixes": data.get("auto_fixes"),
        "changes": data.get("changes"),
        "processes": data.get("processes"),
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
        return path
    except OSError:
        return None


def _bar(v) -> str:
    v = max(0, min(100, float(v or 0)))
    return f'<div class="bar"><span style="width:{v:.1f}%"></span></div>'


def export_html(data: dict) -> str | None:
    reports_dir = _get_export_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    computer = str(data.get("system", {}).get("computer_name", "unknown")).replace(" ", "_")
    path = os.path.join(reports_dir, f"report_{computer}_{ts}.html")

    s = data.get("system") or {}
    c = data.get("cpu") or {}
    r = data.get("ram") or {}
    h = data.get("health") or {}
    n = data.get("network") or {}
    rc = data.get("root_cause") or {}
    disks = data.get("disk") or []
    procs = data.get("processes") or {}
    fixes = data.get("auto_fixes") or []
    changes = data.get("changes") or []
    score = int(h.get("score", 0) or 0)
    score_color = "#86efac" if score >= 85 else ("#e3b341" if score >= 60 else "#f85149")

    disk_rows = "".join(
        f"<tr><td>{escape(str(d.get('device','—')))}</td>"
        f"<td>{float(d.get('usage_percent',0)):.1f}%</td>"
        f"<td>{float(d.get('free_gb',0)):.1f} GB</td>"
        f"<td>{escape(str(d.get('status','—')))}</td>"
        f"<td>{_bar(d.get('usage_percent',0))}</td></tr>"
        for d in disks
    ) or '<tr><td colspan="5">No storage data</td></tr>'

    cpu_rows = "".join(
        f"<tr><td>{escape(str(x.get('name','?')))}</td>"
        f"<td>{float(x.get('cpu_percent',0)):.1f}%</td></tr>"
        for x in (procs.get("top_cpu") or [])[:8]
    ) or '<tr><td colspan="2">No process data</td></tr>'

    ram_rows = "".join(
        f"<tr><td>{escape(str(x.get('name','?')))}</td>"
        f"<td>{float(x.get('memory_percent',0)):.2f}%</td></tr>"
        for x in (procs.get("top_ram") or [])[:8]
    ) or '<tr><td colspan="2">No process data</td></tr>'

    issues = rc.get("issues") or []
    issue_html = "".join(
        f'<div class="issue"><b>!</b><span>{escape(str(x))}</span></div>'
        for x in issues
    ) or '<div class="issue good"><b>✓</b><span>No root-cause findings — baseline healthy.</span></div>'

    fix_html = "".join(
        f'<div class="issue {"good" if x.get("success") else "warn"}">'
        f'<b>{"✓" if x.get("success") else "·"}</b>'
        f'<span>{escape(str(x.get("action", "Action")))}'
        f' — {escape(str(x.get("details", "")))}</span></div>'
        for x in fixes
    ) or '<div class="muted">No remediation actions recorded.</div>'

    changes_html = ""
    if changes:
        changes_html = (
            "<section><h2>DELTA vs LAST SESSION</h2><div class='panel'><ul>"
            + "".join(f"<li>{escape(str(ch))}</li>" for ch in changes)
            + "</ul></div></section>"
        )

    gw = n.get("gateway_latency") or {}
    inet = n.get("internet_latency") or {}
    gw_ms = gw.get("avg_ms") if isinstance(gw, dict) else gw
    inet_ms = inet.get("avg_ms") if isinstance(inet, dict) else inet

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    doc = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>ITOps Command — Endpoint Report</title>
<style>
:root{{--bg:#0a0a0b;--panel:#121214;--panel2:#1a1a1e;--line:#26262b;--text:#f4f4f5;--muted:#a1a1aa;--cyan:#c8ccd4;--ok:#86efac;--warn:#e3b341;--bad:#f85149}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 80% 0%,#1a1a1e,#0a0a0b 45%);color:var(--text);font:14px "Segoe UI",Arial,sans-serif}}
.wrap{{max-width:1180px;margin:auto;padding:34px}}
.top{{display:flex;justify-content:space-between;align-items:end;border-bottom:1px solid var(--line);padding-bottom:24px}}
.brand{{font-size:29px;font-weight:800}}.brand span{{color:var(--cyan)}}
.muted,.sub,.stamp{{color:var(--muted)}}.stamp{{font:12px Consolas,monospace;text-align:right}}
.hero{{display:grid;grid-template-columns:220px 1fr;gap:18px;margin:24px 0}}
.score,.hero-info,.card,.panel{{background:var(--panel);border:1px solid var(--line);border-radius:16px}}
.score{{padding:22px;text-align:center;background:linear-gradient(145deg,#1a1a1e,#121214)}}
.score .num{{font-size:54px;font-weight:800;color:{score_color}}}.score small{{color:var(--muted)}}
.hero-info{{padding:22px}}
.grid4{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.card{{padding:17px}}.label{{font:11px Consolas,monospace;color:var(--muted)}}
.value{{font-size:24px;font-weight:750;margin:6px 0}}
section{{margin-top:22px}}h2{{font-size:13px;letter-spacing:.8px;color:#b9c7d6;text-transform:uppercase}}
.panel{{padding:18px}}table{{width:100%;border-collapse:collapse}}
th,td{{padding:11px 9px;border-bottom:1px solid #17222e;text-align:left}}
th{{font:11px Consolas,monospace;color:var(--muted)}}
.bar{{height:5px;background:#17222e;border-radius:99px;min-width:120px;overflow:hidden}}
.bar span{{display:block;height:100%;background:var(--cyan);border-radius:99px}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.issue{{display:flex;gap:10px;padding:12px;border:1px solid #26303c;background:var(--panel2);border-radius:10px;margin:8px 0}}
.issue b{{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;background:#3a2020;color:var(--bad);flex-shrink:0}}
.issue.good b{{background:#123226;color:var(--ok)}}.issue.warn b{{background:#332a12;color:var(--warn)}}
.footer{{margin-top:28px;padding-top:18px;border-top:1px solid var(--line);display:flex;justify-content:space-between;color:var(--muted);font:11px Consolas,monospace}}
@media(max-width:800px){{.wrap{{padding:18px}}.hero,.cols{{grid-template-columns:1fr}}.grid4{{grid-template-columns:1fr 1fr}}.top{{display:block}}.stamp{{text-align:left;margin-top:10px}}}}
</style></head><body><div class="wrap">
<div class="top"><div><div class="brand">ITOps <span>COMMAND</span></div>
<div class="sub">Endpoint Diagnostic &amp; Operations Report · v1.6.2</div></div>
<div class="stamp">GENERATED<br>{escape(stamp)}</div></div>
<div class="hero">
  <div class="score"><div class="label">POSTURE SCORE</div>
  <div class="num">{score}</div>
  <small>/ 100 · {escape(str(h.get('status','Unknown')))}</small></div>
  <div class="hero-info">
    <div class="label">ENDPOINT</div>
    <h1 style="margin:7px 0 4px">{escape(str(s.get('computer_name','Unknown')))}</h1>
    <div class="sub">{escape(str(s.get('username','')))} · {escape(str((s.get('os') or {}).get('name','OS')))} {escape(str((s.get('os') or {}).get('release','')))}</div>
    <div style="margin-top:20px" class="grid4">
      <div><div class="label">CPU</div><b>{float(c.get('usage_percent',0)):.1f}%</b></div>
      <div><div class="label">MEMORY</div><b>{float(r.get('usage_percent',0)):.1f}%</b></div>
      <div><div class="label">ADAPTER</div><b>{escape(str(n.get('adapter','—')))}</b></div>
      <div><div class="label">NETWORK</div><b>{escape(str(n.get('status','—')))}</b></div>
    </div>
  </div>
</div>
<div class="grid4">
  <div class="card"><div class="label">CPU MODEL</div><div class="value" style="font-size:17px">{escape(str(c.get('name','—')))}</div>
  <div class="sub">{c.get('cores', c.get('physical_cores','—'))} cores · {c.get('threads', c.get('logical_cores','—'))} threads</div></div>
  <div class="card"><div class="label">RAM</div><div class="value">{float(r.get('total_gb',0)):.1f} GB</div>
  <div class="sub">{float(r.get('available_gb',0)):.1f} GB available</div></div>
  <div class="card"><div class="label">GATEWAY</div><div class="value" style="font-size:18px">{escape(str(n.get('gateway','—')))}</div>
  <div class="sub">{escape(str(n.get('ip','—')))} · latency {gw_ms if gw_ms is not None else 'n/a'} ms</div></div>
  <div class="card"><div class="label">ROOT CAUSE</div><div class="value" style="font-size:18px">{escape(str(rc.get('status','—')))}</div>
  <div class="sub">{len(issues)} finding(s) · internet {inet_ms if inet_ms is not None else 'n/a'} ms</div></div>
</div>
<section><h2>Storage Health</h2><div class="panel"><table>
<thead><tr><th>DRIVE</th><th>USED</th><th>FREE</th><th>STATUS</th><th>PRESSURE</th></tr></thead>
<tbody>{disk_rows}</tbody></table></div></section>
<section class="cols">
  <div><h2>Root Cause &amp; Findings</h2><div class="panel">{issue_html}</div></div>
  <div><h2>Remediation</h2><div class="panel">{fix_html}</div></div>
</section>
<section class="cols">
  <div><h2>Top CPU Processes</h2><div class="panel"><table>
  <thead><tr><th>PROCESS</th><th>CPU</th></tr></thead><tbody>{cpu_rows}</tbody></table></div></div>
  <div><h2>Top Memory Processes</h2><div class="panel"><table>
  <thead><tr><th>PROCESS</th><th>MEMORY</th></tr></thead><tbody>{ram_rows}</tbody></table></div></div>
</section>
<section><h2>Network Path</h2><div class="panel"><table>
<tr><th>ADAPTER</th><td>{escape(str(n.get('adapter','—')))}</td></tr>
<tr><th>IP ADDRESS</th><td>{escape(str(n.get('ip','—')))}</td></tr>
<tr><th>GATEWAY</th><td>{escape(str(n.get('gateway','—')))}</td></tr>
<tr><th>STATUS</th><td>{escape(str(n.get('status','—')))}</td></tr>
<tr><th>GATEWAY LATENCY</th><td>{gw_ms if gw_ms is not None else 'n/a'} ms</td></tr>
<tr><th>INTERNET LATENCY</th><td>{inet_ms if inet_ms is not None else 'n/a'} ms</td></tr>
</table></div></section>
{changes_html}
<div class="footer"><span>ITOps Command · Local Operations Platform · v1.6.2</span>
<span>NO CLOUD EGRESS · INTERNAL</span></div>
</div></body></html>"""

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(doc)
        return path
    except OSError:
        return None


def export_report(data: dict) -> dict:
    return {"json": export_json(data), "html": export_html(data)}
