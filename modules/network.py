"""
Network diagnostics — silent (no CMD).

Rule: if DNS resolves public names OR TCP/HTTPS works, Internet is OK.
ICMP ping alone is NOT trusted (many ISPs block it).
"""

from __future__ import annotations

import re
import socket
import time
import urllib.error
import urllib.request

import psutil

from modules.win_silent import run_silent


def _parse_ping(text: str) -> tuple[float | None, float]:
    avg = None
    loss = 0.0
    m_avg = re.search(r"Average\s*=\s*(\d+)\s*ms", text, re.I)
    if not m_avg:
        m_avg = re.search(r"Average\s*=\s*(\d+)", text, re.I)
    if m_avg:
        avg = float(m_avg.group(1))
    m_loss = re.search(r"\((\d+)%\s*(?:loss|lost)\)", text, re.I)
    if not m_loss:
        m_loss = re.search(r"Lost\s*=\s*\d+\s*\((\d+)%", text, re.I)
    if m_loss:
        loss = float(m_loss.group(1))
    if avg is None:
        times = [float(x) for x in re.findall(r"[=<]\s*(\d+)\s*ms", text, re.I)]
        if times:
            avg = sum(times) / len(times)
    return avg, loss


def ping_host(host: str, count: int = 2) -> dict:
    try:
        r = run_silent(["ping", "-n", str(count), "-w", "1000", host], timeout=5)
        text = (r.stdout or "") + (r.stderr or "")
        avg, loss = _parse_ping(text)
        reachable = ("TTL=" in text or "ttl=" in text) or (
            r.returncode == 0 and avg is not None
        )
        if reachable and avg is None:
            avg = 0.0
        return {
            "avg_ms": avg,
            "loss_percent": loss,
            "reachable": bool(reachable),
            "method": "icmp",
        }
    except Exception:
        return {
            "avg_ms": None,
            "loss_percent": 100.0,
            "reachable": False,
            "method": "icmp",
        }


def tcp_probe(host: str, port: int = 443, timeout: float = 2.0) -> dict:
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
        ms = round((time.perf_counter() - t0) * 1000)
        return {
            "avg_ms": float(ms),
            "loss_percent": 0.0,
            "reachable": True,
            "method": f"tcp:{port}",
        }
    except OSError:
        return {
            "avg_ms": None,
            "loss_percent": 100.0,
            "reachable": False,
            "method": f"tcp:{port}",
        }


def http_probe(url: str = "http://www.msftconnecttest.com/connecttest.txt", timeout: float = 2.5) -> dict:
    """Windows NCSI-style connectivity check (HTTP, no ICMP)."""
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ITOps-Command/1.4"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(64)
            ms = round((time.perf_counter() - t0) * 1000)
            ok = getattr(resp, "status", 200) == 200
            return {
                "avg_ms": float(ms),
                "loss_percent": 0.0 if ok else 100.0,
                "reachable": bool(ok),
                "method": "http",
            }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
        return {
            "avg_ms": None,
            "loss_percent": 100.0,
            "reachable": False,
            "method": "http",
        }


def dns_ok() -> bool:
    for host in ("www.msftconnecttest.com", "dns.google", "one.one.one.one", "www.google.com"):
        try:
            socket.setdefaulttimeout(1.5)
            socket.gethostbyname(host)
            return True
        except OSError:
            continue
    return False


def _pick_adapter() -> dict:
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    candidates = []

    for name, addr_list in addrs.items():
        st = stats.get(name)
        if st and not st.isup:
            continue
        ipv4 = None
        mac = None
        for a in addr_list:
            fam = getattr(a, "family", None)
            if fam == socket.AF_INET:
                if a.address and not a.address.startswith("127."):
                    ipv4 = a.address
            if hasattr(psutil, "AF_LINK") and fam == psutil.AF_LINK:
                mac = a.address
            elif fam == 17 or str(fam) == "AddressFamily.AF_PACKET":
                mac = a.address

        if not ipv4:
            continue

        score = 0
        low = name.lower()
        if "wi-fi" in low or "wifi" in low or "wlan" in low:
            score += 50
        if "ethernet" in low and "vethernet" not in low:
            score += 40
        if any(x in low for x in ("virtual", "vbox", "vmware", "hyper-v", "loopback", "bluetooth")):
            score -= 80
        if ipv4.startswith(("192.168.", "10.")):
            score += 10
        if ipv4.startswith("192.168.56."):
            score -= 40
        if ipv4.startswith("169.254."):
            score -= 60

        candidates.append(
            {"adapter": name, "ip": ipv4, "mac": mac or "n/a", "score": score}
        )

    if not candidates:
        return {"adapter": "Unknown", "ip": "n/a", "mac": "n/a"}
    candidates.sort(key=lambda x: x["score"], reverse=True)
    best = candidates[0]
    return {"adapter": best["adapter"], "ip": best["ip"], "mac": best["mac"]}


def _default_gateway() -> str | None:
    try:
        r = run_silent(["ipconfig"], timeout=8)
        text = r.stdout or ""
        for gw in re.findall(
            r"Default Gateway[.\s]*:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)",
            text,
            re.I,
        ):
            if gw and not gw.startswith("0."):
                return gw
        r2 = run_silent(["route", "print", "0.0.0.0"], timeout=6)
        m = re.search(
            r"0\.0\.0\.0\s+0\.0\.0\.0\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)",
            r2.stdout or "",
        )
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def _probe_internet() -> dict:
    """HTTP → TCP 443 → ICMP → DNS."""
    h = http_probe()
    if h["reachable"]:
        return {**h, "note": None}

    for host in ("1.1.1.1", "8.8.8.8", "9.9.9.9"):
        t = tcp_probe(host, 443)
        if t["reachable"]:
            return {**t, "note": "TCP 443 OK"}

    for host in ("1.1.1.1", "8.8.8.8"):
        p = ping_host(host, count=1)
        if p["reachable"]:
            return {**p, "note": None}

    if dns_ok():
        return {
            "avg_ms": None,
            "loss_percent": 0.0,
            "reachable": True,
            "method": "dns",
            "note": "DNS OK",
        }

    return {
        "avg_ms": None,
        "loss_percent": 100.0,
        "reachable": False,
        "method": "none",
        "note": "All probes failed",
    }


def get_network_info() -> dict:
    adapter = _pick_adapter()
    gateway = _default_gateway() or "n/a"

    gw_result = (
        ping_host(gateway, count=1)
        if gateway != "n/a"
        else {"avg_ms": None, "loss_percent": 100.0, "reachable": False, "method": "icmp"}
    )

    dns = dns_ok()
    inet_result = _probe_internet()

    gateway_ok = bool(gw_result.get("reachable"))
    # HARD RULE: DNS success means internet path works
    internet_ok = bool(inet_result.get("reachable")) or bool(dns)

    if internet_ok:
        status = "Internet OK"
    elif gateway_ok:
        status = "Internet Unreachable"
    else:
        status = "Gateway Issue"

    return {
        "adapter": adapter["adapter"],
        "ip": adapter["ip"],
        "mac": adapter["mac"],
        "gateway": gateway,
        "gateway_ok": gateway_ok,
        "dns_ok": dns,
        "internet_ok": internet_ok,
        "status": status,
        "gateway_latency": {
            "avg_ms": gw_result.get("avg_ms"),
            "loss_percent": gw_result.get("loss_percent", 0),
            "reachable": gateway_ok,
        },
        "internet_latency": {
            "avg_ms": inet_result.get("avg_ms"),
            "loss_percent": 0.0 if internet_ok else 100.0,
            "reachable": internet_ok,
            "method": inet_result.get("method") if internet_ok else "none",
            "note": inet_result.get("note"),
        },
    }
