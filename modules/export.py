import json
import os
from datetime import datetime
from modules.paths import get_app_dir


def _get_export_dir():
    """Return folder for exported reports (next to .exe or project root)."""
    reports_dir = os.path.join(get_app_dir(), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir


def export_json(data):
    """Export full report as JSON."""
    reports_dir = _get_export_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    computer = data["system"].get("computer_name", "unknown").replace(" ", "_")
    filename = f"report_{computer}_{timestamp}.json"
    path = os.path.join(reports_dir, filename)

    # Build a clean serializable version
    export_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "system": data.get("system"),
        "cpu": data.get("cpu"),
        "ram": data.get("ram"),
        "disk": data.get("disk"),
        "network": {
            "adapter": data["network"].get("adapter"),
            "ip": data["network"].get("ip"),
            "gateway": data["network"].get("gateway"),
            "mac": data["network"].get("mac"),
            "status": data["network"].get("status"),
            "gateway_ok": data["network"].get("gateway_ok"),
            "dns_ok": data["network"].get("dns_ok"),
            "internet_ok": data["network"].get("internet_ok"),
            "gateway_latency": data["network"].get("gateway_latency"),
            "internet_latency": data["network"].get("internet_latency"),
        },
        "health": data.get("health"),
        "root_cause": data.get("root_cause"),
        "fix_plan": data.get("fix_plan"),
        "auto_fixes": data.get("auto_fixes"),
        "changes": data.get("changes"),
        "processes": data.get("processes"),
    }

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        return path
    except OSError:
        return None


def export_html(data):
    """Export a clean HTML report."""
    reports_dir = _get_export_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    computer = data["system"].get("computer_name", "unknown").replace(" ", "_")
    filename = f"report_{computer}_{timestamp}.html"
    path = os.path.join(reports_dir, filename)

    system = data["system"]
    cpu = data["cpu"]
    ram = data["ram"]
    disks = data["disk"]
    health = data["health"]
    network = data["network"]
    root_cause = data["root_cause"]
    fix_plan = data["fix_plan"]
    auto_fixes = data.get("auto_fixes", [])
    changes = data.get("changes", [])
    processes = data.get("processes", {})

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ITOps Assistant Report - {system.get('computer_name')}</title>
<style>
    body {{ font-family: Segoe UI, Arial, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; }}
    .container {{ max-width: 900px; margin: auto; }}
    h1 {{ color: #38bdf8; border-bottom: 2px solid #1e293b; padding-bottom: 10px; }}
    h2 {{ color: #7dd3fc; margin-top: 30px; }}
    .card {{ background: #1e293b; border-radius: 10px; padding: 16px 20px; margin: 12px 0; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .label {{ color: #94a3b8; font-size: 0.85em; }}
    .value {{ font-size: 1.1em; font-weight: 600; }}
    .ok {{ color: #4ade80; }}
    .warn {{ color: #fbbf24; }}
    .bad {{ color: #f87171; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #334155; }}
    th {{ color: #94a3b8; font-weight: 500; }}
    .badge {{ display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.8em; }}
    .badge-ok {{ background: #14532d; color: #4ade80; }}
    .badge-warn {{ background: #713f12; color: #fbbf24; }}
    .badge-bad {{ background: #7f1d1d; color: #f87171; }}
    footer {{ margin-top: 40px; color: #64748b; font-size: 0.85em; text-align: center; }}
</style>
</head>
<body>
<div class="container">
    <h1>ITOps Assistant Report</h1>
    <p class="label">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Host: {system.get('computer_name')}</p>

    <h2>System</h2>
    <div class="card grid">
        <div><div class="label">Computer</div><div class="value">{system.get('computer_name')}</div></div>
        <div><div class="label">User</div><div class="value">{system.get('username')}</div></div>
        <div><div class="label">OS</div><div class="value">{system.get('os', {}).get('name')} {system.get('os', {}).get('release')}</div></div>
        <div><div class="label">Health Score</div><div class="value">{health.get('score')}/100 — {health.get('status')}</div></div>
    </div>

    <h2>CPU & RAM</h2>
    <div class="card grid">
        <div><div class="label">CPU</div><div class="value">{cpu.get('name')}</div></div>
        <div><div class="label">Usage</div><div class="value">{cpu.get('usage_percent')}%</div></div>
        <div><div class="label">Cores / Threads</div><div class="value">{cpu.get('physical_cores')} / {cpu.get('logical_cores')}</div></div>
        <div><div class="label">RAM Usage</div><div class="value">{ram.get('usage_percent')}% ({ram.get('available_gb')} GB free)</div></div>
    </div>

    <h2>Disks</h2>
    <div class="card">
        <table>
            <tr><th>Drive</th><th>Total</th><th>Used</th><th>Free</th><th>Usage</th><th>Status</th></tr>
"""

    for d in disks:
        status_class = "badge-ok" if d["status"] == "Healthy" else ("badge-bad" if d["status"] == "Critical" else "badge-warn")
        html += f"""            <tr>
                <td>{d['device']}</td>
                <td>{d['total_gb']} GB</td>
                <td>{d['used_gb']} GB</td>
                <td>{d['free_gb']} GB</td>
                <td>{d['usage_percent']}%</td>
                <td><span class="badge {status_class}">{d['status']}</span></td>
            </tr>
"""

    html += f"""        </table>
    </div>

    <h2>Network</h2>
    <div class="card grid">
        <div><div class="label">Adapter</div><div class="value">{network.get('adapter')}</div></div>
        <div><div class="label">IP</div><div class="value">{network.get('ip')}</div></div>
        <div><div class="label">Gateway</div><div class="value">{network.get('gateway')}</div></div>
        <div><div class="label">Status</div><div class="value">{network.get('status')}</div></div>
        <div><div class="label">Gateway Latency</div><div class="value">{(network.get('gateway_latency') or {}).get('avg_ms', 'N/A')} ms</div></div>
        <div><div class="label">Internet Latency</div><div class="value">{(network.get('internet_latency') or {}).get('avg_ms', 'N/A')} ms</div></div>
    </div>

    <h2>Root Cause & Fixes</h2>
    <div class="card">
        <p><strong>Status:</strong> {root_cause.get('status')}</p>
"""

    if root_cause.get("issues"):
        html += "<p><strong>Issues:</strong></p><ul>"
        for issue in root_cause["issues"]:
            html += f"<li>{issue}</li>"
        html += "</ul>"

    if fix_plan:
        html += "<p><strong>Fix Plan:</strong></p><ul>"
        for fix in fix_plan:
            html += f"<li><strong>[{fix['priority']}]</strong> {fix['issue']} → {fix['fix']}</li>"
        html += "</ul>"

    if auto_fixes:
        html += "<p><strong>Auto Fixes:</strong></p><ul>"
        for fix in auto_fixes:
            mark = "✔" if fix.get("success") else "❌"
            html += f"<li>{mark} {fix.get('action')} — {fix.get('details', '')}</li>"
        html += "</ul>"

    html += "</div>"

    # Processes
    html += """
    <h2>Top Processes</h2>
    <div class="card">
        <h3 style="margin-top:0;color:#94a3b8;">CPU</h3>
        <table>
            <tr><th>Process</th><th>CPU</th><th>RAM</th></tr>
"""
    for p in processes.get("top_cpu", []):
        html += f"<tr><td>{p['name']}</td><td>{p['cpu_percent']}%</td><td>{p['memory_percent']}%</td></tr>"

    html += """
        </table>
        <h3 style="color:#94a3b8;">RAM</h3>
        <table>
            <tr><th>Process</th><th>RAM</th><th>CPU</th></tr>
"""
    for p in processes.get("top_ram", []):
        html += f"<tr><td>{p['name']}</td><td>{p['memory_percent']}%</td><td>{p['cpu_percent']}%</td></tr>"

    html += """
        </table>
    </div>
"""

    if changes:
        html += """
    <h2>Changes Since Last Run</h2>
    <div class="card"><ul>
"""
        for c in changes:
            html += f"<li>{c}</li>"
        html += "</ul></div>"

    html += f"""
    <footer>ITOps Assistant • {datetime.now().strftime("%Y-%m-%d %H:%M")}</footer>
</div>
</body>
</html>
"""

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path
    except OSError:
        return None


def export_report(data):
    """
    Export both JSON and HTML reports.
    Returns dict with paths.
    """
    json_path = export_json(data)
    html_path = export_html(data)

    return {
        "json": json_path,
        "html": html_path
    }
