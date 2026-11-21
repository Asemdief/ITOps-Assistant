"""
ITOps Command — Endpoint Security Posture module.

Design rules (same spirit as the rest of the product):
  * READ-ONLY. Scanning never changes the machine. Fixes live in security_fix.py
    and are opt-in, previewed, journaled and reversible.
  * Locale-independent. Registry (winreg) first; one batched PowerShell call that
    returns JSON objects (never parsed localized text); SIDs not group names.
  * No console flash. PowerShell only through win_silent.
  * Honest. A check that cannot be evaluated is UNKNOWN / NEEDS_ADMIN and is
    excluded from the score but reported as lower *coverage* — never guessed.

Each finding carries: id, severity, status, expected vs actual, evidence,
remediation, an optional reversible fix descriptor, and a stable fingerprint.

NOTE: `framework_area` is a plain-language area label (e.g. "Account Policies")
inspired by common hardening baselines. It is NOT an official CIS control ID.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import socket
from datetime import date, datetime
from typing import Any, Callable

from modules.registry_io import WinRegistry, is_admin

SEV_WEIGHT = {"CRITICAL": 10, "HIGH": 6, "MEDIUM": 3, "LOW": 1}
SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
SCORED = ("PASS", "WARN", "FAIL")

# ---------------------------------------------------------------------------
# Catalog + check registry (declarative, definition order == scan order)
# ---------------------------------------------------------------------------
CATALOG: dict[str, dict[str, Any]] = {}
CHECKS: list[tuple[str, Callable[["Ctx"], tuple]]] = []


def check(cid, title, category, severity, expected, remediation, area):
    def deco(fn):
        CATALOG[cid] = {
            "id": cid,
            "title": title,
            "category": category,
            "severity": severity,
            "expected": expected,
            "remediation": remediation,
            "framework_area": area,
        }
        CHECKS.append((cid, fn))
        return fn

    return deco


def dword_fix(hive, path, name, value, impact, *, reboot=False):
    """Reversible registry fix descriptor consumed by security_fix.apply_fix."""
    return {
        "kind": "registry_dword",
        "hive": hive,
        "path": path,
        "name": name,
        "value": value,
        "impact": impact,
        "needs_admin": hive == "HKLM",
        "reboot_required": reboot,
    }


class Ctx:
    def __init__(self, reg, ps, admin, signatures, listeners, now):
        self.reg = reg
        self.ps: dict[str, Any] = ps or {}
        self.admin = admin
        self.signatures = signatures
        self.listeners = listeners
        self.now = now


def _as_list(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


# ---------------------------------------------------------------------------
# Data collectors (the only places that touch the OS beyond the registry)
# ---------------------------------------------------------------------------
_PS_MAIN = "\n".join(
    [
        "$ErrorActionPreference='SilentlyContinue'",
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8",
        "$r=[ordered]@{}",
        "$mp=Get-MpComputerStatus",
        "$r.defender=@{ok=($null -ne $mp);rtp=$mp.RealTimeProtectionEnabled;sigAge=$mp.AntivirusSignatureAge;tamper=$mp.IsTamperProtected}",
        "$r.av=@(Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct | ForEach-Object {$_.displayName})",
        "$r.admins=@(Get-LocalGroupMember -SID S-1-5-32-544 | ForEach-Object {$_.Name})",
        "$r.users=@(Get-LocalUser | ForEach-Object {@{sid=$_.SID.Value;name=$_.Name;enabled=[bool]$_.Enabled}})",
        "$hf=Get-HotFix | Where-Object {$_.InstalledOn} | Sort-Object InstalledOn -Descending | Select-Object -First 1",
        "$r.lastHotfix=$(if($hf){$hf.InstalledOn.ToString('yyyy-MM-dd')}else{$null})",
        "$r.bitlocker=$(try{(New-Object -ComObject Shell.Application).NameSpace($env:SystemDrive+'\\').Self.ExtendedProperty('System.Volume.BitLockerProtection')}catch{$null})",
    ]
)
_PS_ADMIN_EXTRA = "$r.exclusions=@((Get-MpPreference).ExclusionPath)"
_PS_TAIL = "ConvertTo-Json -InputObject $r -Depth 4 -Compress"


def collect_ps(admin: bool) -> dict[str, Any]:
    """One batched PowerShell call -> dict. Never raises."""
    from modules.win_silent import run_powershell

    script = _PS_MAIN + ("\n" + _PS_ADMIN_EXTRA if admin else "") + "\n" + _PS_TAIL
    try:
        cp = run_powershell(script, timeout=90, encoding="utf-8")
        out = (cp.stdout or "").strip()
        if cp.returncode != 0 or not out:
            return {"_error": f"powershell rc={cp.returncode} {(cp.stderr or '')[:120]}"}
        return json.loads(out)
    except Exception as e:  # noqa: BLE001 — collectors must never crash a scan
        return {"_error": f"{type(e).__name__}: {e}"}


def check_signatures(paths: list[str]) -> dict[str, dict[str, str]] | None:
    """Authenticode status for up to 40 files. Payload is base64 (no quoting bugs)."""
    from modules.win_silent import run_powershell

    paths = [p for p in dict.fromkeys(paths) if p][:40]
    if not paths:
        return {}
    b64 = base64.b64encode(json.dumps(paths).encode("utf-8")).decode("ascii")
    script = (
        "$ErrorActionPreference='SilentlyContinue';"
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
        f"$p=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b64}'))|ConvertFrom-Json;"
        "$o=@($p|ForEach-Object{$s=Get-AuthenticodeSignature -LiteralPath $_;"
        "@{path=[string]$_;status=[string]$s.Status;signer=[string]$s.SignerCertificate.Subject}});"
        "ConvertTo-Json -InputObject $o -Depth 3 -Compress"
    )
    try:
        cp = run_powershell(script, timeout=60, encoding="utf-8")
        out = (cp.stdout or "").strip()
        if cp.returncode != 0 or not out:
            return None
        return {r["path"]: r for r in _as_list(json.loads(out))}
    except Exception:  # noqa: BLE001
        return None


def collect_listeners() -> list[dict[str, Any]] | None:
    """Listening TCP sockets with owning process name. None if unavailable."""
    try:
        import psutil
    except ImportError:
        return None
    out: list[dict[str, Any]] = []
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.status != "LISTEN" or not c.laddr:
                continue
            name = ""
            if c.pid:
                try:
                    name = psutil.Process(c.pid).name()
                except Exception:  # noqa: BLE001
                    name = ""
            out.append({"ip": c.laddr.ip, "port": c.laddr.port, "pid": c.pid, "process": name})
    except Exception:  # noqa: BLE001
        return None
    return out


# ---------------------------------------------------------------------------
# Checks — each returns (status, actual, evidence[, fix])
# ---------------------------------------------------------------------------
def _defender(c: Ctx) -> dict:
    return c.ps.get("defender") or {}


def _third_party_av(c: Ctx) -> list[str]:
    return [n for n in _as_list(c.ps.get("av")) if n and "defender" not in str(n).lower()]


# ---- Endpoint Protection --------------------------------------------------
@check("ITC-001", "Antivirus real-time protection", "Endpoint Protection", "CRITICAL",
       "Real-time protection enabled",
       "Enable Microsoft Defender real-time protection (Windows Security > Virus & threat protection) or ensure the third-party AV is active.",
       "Malware Defenses")
def c_rtp(c: Ctx):
    if c.ps.get("_error"):
        return "UNKNOWN", "Could not query AV status", c.ps["_error"]
    d, tp = _defender(c), _third_party_av(c)
    if d.get("rtp") is True:
        return "PASS", "Enabled", "Defender RealTimeProtectionEnabled=True"
    if tp:
        return "WARN", "Defender passive; third-party AV present", "Registered AV: " + ", ".join(tp[:3]) + " (verify it is active and updating)"
    if d.get("ok"):
        return "FAIL", "Disabled", "Defender RealTimeProtectionEnabled=False and no other AV registered"
    return "FAIL", "No antivirus product reported", "Neither Defender nor Security Center reported an AV"


@check("ITC-002", "Antivirus signatures freshness", "Endpoint Protection", "HIGH",
       "Signatures <= 7 days old",
       "Run Windows Update / 'Check for updates' in Windows Security to refresh Defender definitions.",
       "Malware Defenses")
def c_sigage(c: Ctx):
    d = _defender(c)
    age = d.get("sigAge")
    if not d.get("ok") or age is None:
        return "UNKNOWN", "Not available", "Defender signature age not reported (third-party AV or restricted)"
    if d.get("rtp") is not True and _third_party_av(c):
        return "UNKNOWN", "Defender is passive", "Signatures belong to the third-party AV"
    age = int(age)
    ev = f"AntivirusSignatureAge={age} day(s)"
    if age <= 7:
        return "PASS", f"{age} day(s)", ev
    if age <= 14:
        return "WARN", f"{age} day(s)", ev
    return "FAIL", f"{age} day(s)", ev


@check("ITC-003", "Defender tamper protection", "Endpoint Protection", "MEDIUM",
       "Tamper protection on",
       "Turn on Tamper Protection in Windows Security > Virus & threat protection settings.",
       "Malware Defenses")
def c_tamper(c: Ctx):
    d = _defender(c)
    t = d.get("tamper")
    if not d.get("ok") or t is None:
        return "UNKNOWN", "Not available", "IsTamperProtected not reported"
    return ("PASS", "On", "IsTamperProtected=True") if t else ("FAIL", "Off", "IsTamperProtected=False")


@check("ITC-004", "Defender exclusions", "Endpoint Protection", "MEDIUM",
       "No path exclusions",
       "Review Defender exclusions and remove any that are not strictly required; attackers often add exclusions to hide payloads.",
       "Malware Defenses")
def c_exclusions(c: Ctx):
    if not c.admin:
        return "NEEDS_ADMIN", "Requires administrator", "Reading Defender exclusions needs elevation"
    ex = [e for e in _as_list(c.ps.get("exclusions")) if e]
    if not ex:
        return "PASS", "None", "ExclusionPath is empty"
    return "WARN", f"{len(ex)} path exclusion(s)", "; ".join(str(e) for e in ex[:5])


# ---- Network & Exposure ---------------------------------------------------
_FW_BASE = r"SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy"
_FW_POL = r"SOFTWARE\Policies\Microsoft\WindowsFirewall"


@check("ITC-010", "Windows Firewall (all profiles)", "Network & Exposure", "HIGH",
       "Domain, Private, Public all enabled",
       "Enable Windows Defender Firewall for Domain, Private and Public profiles.",
       "Host Firewall")
def c_firewall(c: Ctx):
    profiles = (("Domain", "DomainProfile"), ("Private", "StandardProfile"), ("Public", "PublicProfile"))
    state: dict[str, Any] = {}
    for label, key in profiles:
        pol = c.reg.get("HKLM", f"{_FW_POL}\\{key}", "EnableFirewall")
        state[label] = pol if pol is not None else c.reg.get("HKLM", f"{_FW_BASE}\\{key}", "EnableFirewall")
    ev = ", ".join(f"{k}={'On' if v == 1 else 'Off' if v == 0 else '?'}" for k, v in state.items())
    off = [k for k, v in state.items() if v == 0]
    if off:
        return "FAIL", "Off: " + ", ".join(off), ev
    if all(v == 1 for v in state.values()):
        return "PASS", "All profiles on", ev
    return "UNKNOWN", "State not readable", ev


_TS = r"SYSTEM\CurrentControlSet\Control\Terminal Server"
_RDP_TCP = _TS + r"\WinStations\RDP-Tcp"


@check("ITC-011", "Remote Desktop exposure", "Network & Exposure", "HIGH",
       "RDP disabled, or enabled with NLA",
       "Disable Remote Desktop if unused; if required, enforce Network Level Authentication and restrict by firewall/VPN.",
       "Remote Access")
def c_rdp(c: Ctx):
    deny = c.reg.get("HKLM", _TS, "fDenyTSConnections")
    if deny is None:
        return "UNKNOWN", "Not readable", "fDenyTSConnections missing"
    if deny == 1:
        return "PASS", "Disabled", "fDenyTSConnections=1"
    nla = c.reg.get("HKLM", _RDP_TCP, "UserAuthentication")
    if nla == 1:
        return "WARN", "Enabled with NLA", "fDenyTSConnections=0, UserAuthentication=1 (restrict exposure)"
    return ("FAIL", "Enabled WITHOUT NLA", "fDenyTSConnections=0, UserAuthentication=0",
            dword_fix("HKLM", _RDP_TCP, "UserAuthentication", 1,
                      "Clients without NLA support can no longer connect via RDP."))


_SMB = r"SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters"


@check("ITC-012", "SMBv1 server protocol", "Network & Exposure", "HIGH",
       "SMBv1 disabled",
       "Disable SMBv1 (Windows Features > SMB 1.0/CIFS, or Set-SmbServerConfiguration -EnableSMB1Protocol $false).",
       "Legacy Protocols")
def c_smb1(c: Ctx):
    v = c.reg.get("HKLM", _SMB, "SMB1")
    if v == 0:
        return "PASS", "Disabled", "LanmanServer SMB1=0"
    if v == 1:
        return ("FAIL", "Enabled", "LanmanServer SMB1=1",
                dword_fix("HKLM", _SMB, "SMB1", 0,
                          "Legacy devices/software that require SMBv1 (old NAS, scanners) will stop working. Restart of the Server service or reboot needed.",
                          reboot=True))
    return "UNKNOWN", "Not explicitly configured", "SMB1 value absent (OS default). Verify with Get-SmbServerConfiguration as admin."


@check("ITC-013", "LLMNR name resolution", "Network & Exposure", "MEDIUM",
       "LLMNR disabled (EnableMulticast=0)",
       "Disable LLMNR via policy (Computer Config > Administrative Templates > Network > DNS Client > Turn off multicast name resolution).",
       "Legacy Protocols")
def c_llmnr(c: Ctx):
    p = r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient"
    v = c.reg.get("HKLM", p, "EnableMulticast")
    if v == 0:
        return "PASS", "Disabled", "EnableMulticast=0"
    return ("FAIL", "Enabled (default)" if v is None else "Enabled", f"EnableMulticast={'unset' if v is None else v}",
            dword_fix("HKLM", p, "EnableMulticast", 0,
                      "Name resolution falls back to DNS only; rarely affects normal networks."))


_CLEARTEXT = {21: "FTP", 23: "Telnet", 5900: "VNC", 5901: "VNC"}
_ADMINSVC = {3389: "RDP", 5985: "WinRM-HTTP", 5986: "WinRM-HTTPS", 1433: "MSSQL", 3306: "MySQL",
             5432: "PostgreSQL", 27017: "MongoDB", 6379: "Redis", 9200: "Elasticsearch"}
_LOOPBACK = {"127.0.0.1", "::1"}


@check("ITC-014", "Risky listening ports", "Network & Exposure", "HIGH",
       "No cleartext/remote-admin services listening on all interfaces",
       "Stop or uninstall unneeded services; bind required ones to localhost or restrict with firewall rules.",
       "Attack Surface")
def c_ports(c: Ctx):
    ls = c.listeners()
    if ls is None:
        return "UNKNOWN", "Could not enumerate sockets", "psutil unavailable or access denied"
    ext = [x for x in ls if x["ip"] not in _LOOPBACK]
    bad = [x for x in ext if x["port"] in _CLEARTEXT]
    warn = [x for x in ext if x["port"] in _ADMINSVC]

    def fmt(xs, table):
        return "; ".join(f"{x['port']}/{table[x['port']]} ({x.get('process') or 'pid ' + str(x.get('pid'))})" for x in xs[:6])

    summary = f"{len(ext)} non-loopback listener(s)"
    if bad:
        return "FAIL", fmt(bad, _CLEARTEXT), summary + ". Listening is not the same as reachable: check the firewall too."
    if warn:
        return "WARN", fmt(warn, _ADMINSVC), summary + ". Listening is not the same as reachable: check the firewall too."
    return "PASS", "None found", summary


# ---- Disk & Boot ----------------------------------------------------------
@check("ITC-020", "BitLocker on system drive", "Disk & Boot", "HIGH",
       "System drive encrypted",
       "Enable BitLocker (or device encryption) on the system drive and back up the recovery key.",
       "Data Protection")
def c_bitlocker(c: Ctx):
    v = c.ps.get("bitlocker")
    if v is None:
        return "UNKNOWN", "Not reported", "Shell BitLockerProtection property unavailable"
    try:
        v = int(v)
    except (TypeError, ValueError):
        return "UNKNOWN", f"Unexpected value {v!r}", "System.Volume.BitLockerProtection"
    if v == 1:
        return "PASS", "Protection on", "System.Volume.BitLockerProtection=1"
    if v == 0:
        return "FAIL", "Not encrypted", "System.Volume.BitLockerProtection=0"
    return "UNKNOWN", f"State code {v}", "System.Volume.BitLockerProtection (suspended/unknown)"


@check("ITC-021", "UEFI Secure Boot", "Disk & Boot", "MEDIUM",
       "Secure Boot enabled",
       "Enable Secure Boot in UEFI firmware (requires UEFI boot mode, not Legacy/CSM).",
       "Platform Integrity")
def c_secureboot(c: Ctx):
    v = c.reg.get("HKLM", r"SYSTEM\CurrentControlSet\Control\SecureBoot\State", "UEFISecureBootEnabled")
    if v == 1:
        return "PASS", "Enabled", "UEFISecureBootEnabled=1"
    if v == 0:
        return "FAIL", "Disabled", "UEFISecureBootEnabled=0"
    return "WARN", "Not reported", "Key absent: Legacy BIOS/CSM boot or unsupported hardware"


# ---- Accounts & Access ----------------------------------------------------
_POL_SYS = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"


@check("ITC-030", "User Account Control (UAC)", "Accounts & Access", "HIGH",
       "UAC enabled; admin prompts not silenced",
       "Enable UAC and keep 'Admin Approval Mode' prompting for elevation.",
       "Account Policies")
def c_uac(c: Ctx):
    lua = c.reg.get("HKLM", _POL_SYS, "EnableLUA")
    if lua is None:
        return "UNKNOWN", "Not readable", "EnableLUA missing"
    if lua == 0:
        return ("FAIL", "Disabled", "EnableLUA=0",
                dword_fix("HKLM", _POL_SYS, "EnableLUA", 1,
                          "Prompts appear for administrative actions again. Reboot required.", reboot=True))
    if c.reg.get("HKLM", _POL_SYS, "ConsentPromptBehaviorAdmin") == 0:
        return "WARN", "Enabled but admins elevate silently", "ConsentPromptBehaviorAdmin=0"
    return "PASS", "Enabled", "EnableLUA=1"


@check("ITC-031", "Local administrators count", "Accounts & Access", "MEDIUM",
       "2 or fewer members",
       "Remove day-to-day users from the local Administrators group; use a separate admin account for elevation.",
       "Account Policies")
def c_admins(c: Ctx):
    if "admins" not in c.ps:
        return "UNKNOWN", "Not available", "Local Administrators membership not returned"
    m = [x for x in _as_list(c.ps.get("admins")) if x]
    ev = ", ".join(m[:8]) or "(none)"
    if len(m) <= 2:
        return "PASS", f"{len(m)} member(s)", ev
    if len(m) <= 4:
        return "WARN", f"{len(m)} member(s)", ev
    return "FAIL", f"{len(m)} member(s)", ev


def _user_by_rid(c: Ctx, rid: str):
    for u in _as_list(c.ps.get("users")):
        if str(u.get("sid", "")).endswith("-" + rid):
            return u
    return None


@check("ITC-032", "Guest account disabled", "Accounts & Access", "MEDIUM",
       "Guest account disabled",
       "Disable the built-in Guest account (lusrmgr.msc or Disable-LocalUser).",
       "Account Policies")
def c_guest(c: Ctx):
    u = _user_by_rid(c, "501")
    if u is None:
        return "UNKNOWN", "Guest account not found", "SID *-501 not listed"
    return ("FAIL", "Enabled", f"{u.get('name')} enabled") if u.get("enabled") else ("PASS", "Disabled", f"{u.get('name')} disabled")


@check("ITC-033", "Built-in Administrator account", "Accounts & Access", "LOW",
       "Built-in Administrator disabled (or renamed + strong password)",
       "Disable the built-in Administrator account and use named admin accounts instead.",
       "Account Policies")
def c_builtin_admin(c: Ctx):
    u = _user_by_rid(c, "500")
    if u is None:
        return "UNKNOWN", "Account not found", "SID *-500 not listed"
    return ("WARN", "Enabled", f"{u.get('name')} enabled") if u.get("enabled") else ("PASS", "Disabled", f"{u.get('name')} disabled")


@check("ITC-034", "Inactivity screen lock", "Accounts & Access", "LOW",
       "Lock after 15 minutes or less",
       "Enforce an inactivity lock of 900 seconds or less (policy 'Interactive logon: Machine inactivity limit').",
       "Session Controls")
def c_screenlock(c: Ctx):
    t = c.reg.get("HKLM", _POL_SYS, "InactivityTimeoutSecs")
    if t is not None:
        if 0 < int(t) <= 900:
            return "PASS", f"{int(t)}s (policy)", "InactivityTimeoutSecs"
        return ("FAIL", f"{int(t)}s (policy)", "InactivityTimeoutSecs exceeds 900 or is 0",
                dword_fix("HKLM", _POL_SYS, "InactivityTimeoutSecs", 900,
                          "Idle sessions lock after 15 minutes."))
    active = c.reg.get("HKCU", r"Control Panel\Desktop", "ScreenSaveActive")
    secure = c.reg.get("HKCU", r"Control Panel\Desktop", "ScreenSaverIsSecure")
    tout = c.reg.get("HKCU", r"Control Panel\Desktop", "ScreenSaveTimeOut")
    try:
        ok = str(active) == "1" and str(secure) == "1" and 0 < int(tout) <= 900
    except (TypeError, ValueError):
        ok = False
    if ok:
        return "PASS", f"{int(tout)}s (screensaver)", "Secure screensaver configured"
    return "WARN", "No enforced inactivity lock found", "May still be configured via power/sign-in settings"


# ---- Credential Protection ------------------------------------------------
@check("ITC-040", "WDigest plaintext credentials", "Credential Protection", "CRITICAL",
       "UseLogonCredential = 0",
       "Set UseLogonCredential to 0 so plaintext passwords are not cached in LSASS memory.",
       "Credential Hardening")
def c_wdigest(c: Ctx):
    p = r"SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest"
    v = c.reg.get("HKLM", p, "UseLogonCredential")
    if v == 1:
        return ("FAIL", "Plaintext caching ON", "UseLogonCredential=1",
                dword_fix("HKLM", p, "UseLogonCredential", 0,
                          "Disables WDigest credential caching; harmless on supported Windows versions."))
    return "PASS", "Off", f"UseLogonCredential={'unset (default off)' if v is None else v}"


@check("ITC-041", "LSA protection (RunAsPPL)", "Credential Protection", "MEDIUM",
       "LSASS runs as protected process",
       "Enable LSA protection (RunAsPPL=1) and reboot; test with your security/EDR drivers first.",
       "Credential Hardening")
def c_lsa(c: Ctx):
    p = r"SYSTEM\CurrentControlSet\Control\Lsa"
    v = c.reg.get("HKLM", p, "RunAsPPL")
    if v in (1, 2):
        return "PASS", "Enabled", f"RunAsPPL={v}"
    return ("WARN", "Not enabled", f"RunAsPPL={'unset' if v is None else v}",
            dword_fix("HKLM", p, "RunAsPPL", 1,
                      "May block unsigned LSA plug-ins or older security drivers. Reboot required; test first.",
                      reboot=True))


# ---- Patching -------------------------------------------------------------
@check("ITC-050", "Last Windows update installed", "Patching", "HIGH",
       "Updates installed within 35 days",
       "Run Windows Update and install pending quality updates; check WSUS/Intune policy if updates are blocked.",
       "Patch Management")
def c_update_age(c: Ctx):
    s = c.ps.get("lastHotfix")
    if not s:
        return "UNKNOWN", "No hotfix history", "Get-HotFix returned no dated entry"
    try:
        d = datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return "UNKNOWN", "Unparseable date", str(s)
    age = (c.now.date() - d).days
    ev = f"Most recent hotfix installed {d.isoformat()}"
    if age <= 35:
        return "PASS", f"{age} day(s) ago", ev
    if age <= 75:
        return "WARN", f"{age} day(s) ago", ev
    return "FAIL", f"{age} day(s) ago", ev


@check("ITC-051", "Pending reboot", "Patching", "LOW",
       "No reboot pending",
       "Restart the machine to finish installing updates.",
       "Patch Management")
def c_reboot(c: Ctx):
    keys = {
        "Windows Update": r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired",
        "Servicing": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending",
    }
    hit = [n for n, p in keys.items() if c.reg.key_exists("HKLM", p)]
    if hit:
        return "WARN", "Reboot pending", "Flag set by: " + ", ".join(hit)
    return "PASS", "None", "No reboot flags present"


# ---- Persistence & Logging ------------------------------------------------
_RUN_KEYS = (
    ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
    ("HKLM", r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
    ("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
)
_EXE_RE = re.compile(r'^\s*(?:"([^"]+)"|(.+?\.(?:exe|com|bat|cmd|scr|vbs|js|ps1))(?=\s|$))', re.I)
_RISKY_LOC = ("\\appdata\\local\\temp\\", "\\temp\\", "\\downloads\\", "\\users\\public\\", "\\$recycle.bin\\")
_BAD_SIG = {"NotSigned", "HashMismatch", "NotTrusted", "Incompatible"}


def parse_command_path(cmd: str) -> str:
    m = _EXE_RE.match(str(cmd or ""))
    if not m:
        return ""
    return os.path.expandvars(m.group(1) or m.group(2) or "")


@check("ITC-060", "Startup programs trust", "Persistence & Logging", "MEDIUM",
       "Autorun entries signed and in trusted locations",
       "Remove unknown autorun entries; investigate anything unsigned or launching from Temp/Downloads/Public.",
       "Persistence")
def c_startup(c: Ctx):
    entries = []
    for hive, path in _RUN_KEYS:
        for name, cmd in c.reg.list_values(hive, path).items():
            entries.append({"name": name, "src": f"{hive}\\Run", "path": parse_command_path(cmd), "cmd": str(cmd)})
    if not entries:
        return "PASS", "No Run-key entries", "Run keys are empty"
    sigs = c.signatures([e["path"] for e in entries if e["path"]])
    unsigned, risky, both = [], [], []
    for e in entries:
        low = e["path"].lower()
        in_risky = any(m in low for m in _RISKY_LOC)
        bad_sig = sigs is not None and (sigs.get(e["path"], {}).get("status") in _BAD_SIG)
        if in_risky:
            risky.append(e["name"])
        if bad_sig:
            unsigned.append(e["name"])
        if in_risky and bad_sig:
            both.append(e["name"])
    note = "" if sigs is not None else " (signature lookup unavailable — path heuristics only)"
    ev = f"{len(entries)} entries{note}"
    if both:
        return "FAIL", "Unsigned in risky location: " + ", ".join(both[:4]), ev
    if unsigned or risky:
        bits = []
        if unsigned:
            bits.append("unsigned: " + ", ".join(unsigned[:4]))
        if risky:
            bits.append("risky path: " + ", ".join(risky[:4]))
        return "WARN", "; ".join(bits), ev
    return "PASS", f"{len(entries)} entries look trusted", ev


@check("ITC-061", "PowerShell script block logging", "Persistence & Logging", "LOW",
       "Script block logging enabled",
       "Enable PowerShell Script Block Logging so malicious scripts leave an audit trail.",
       "Audit & Logging")
def c_psblock(c: Ctx):
    p = r"SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging"
    v = c.reg.get("HKLM", p, "EnableScriptBlockLogging")
    if v == 1:
        return "PASS", "Enabled", "EnableScriptBlockLogging=1"
    return ("WARN", "Not enabled", f"EnableScriptBlockLogging={'unset' if v is None else v}",
            dword_fix("HKLM", p, "EnableScriptBlockLogging", 1,
                      "Adds PowerShell activity to the Event Log (slightly more log volume)."))


# ---------------------------------------------------------------------------
# Scoring + packaging
# ---------------------------------------------------------------------------
def fingerprint(f: dict) -> str:
    raw = f"{f['id']}|{f['status']}|{f['actual']}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8].upper()


def _build(cid: str, status: str, actual: str, evidence: str = "", fix: dict | None = None) -> dict:
    f = dict(CATALOG[cid])
    f.update(status=status, actual=actual, evidence=evidence)
    f["fix"] = fix if status in ("FAIL", "WARN") else None
    f["fingerprint"] = fingerprint(f)
    return f


def grade_for(score: int | None) -> str:
    if score is None:
        return "N/A"
    return "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"


def summarize(findings: list[dict], admin: bool, now: datetime) -> dict[str, Any]:
    earned = possible = 0.0
    for f in findings:
        if f["status"] in SCORED:
            w = SEV_WEIGHT[f["severity"]]
            possible += w
            earned += w if f["status"] == "PASS" else (w * 0.5 if f["status"] == "WARN" else 0)
    score = round(100 * earned / possible) if possible else None
    capped = False
    if score is not None and any(f["severity"] == "CRITICAL" and f["status"] == "FAIL" for f in findings):
        if score > 59:
            score, capped = 59, True
    evaluated = sum(1 for f in findings if f["status"] in SCORED)
    counts = {s: sum(1 for f in findings if f["status"] == s) for s in ("PASS", "WARN", "FAIL", "UNKNOWN", "NEEDS_ADMIN")}
    risks = sorted((f for f in findings if f["status"] in ("FAIL", "WARN")),
                   key=lambda f: (SEV_ORDER[f["severity"]], f["status"] != "FAIL", f["id"]))
    host = socket.gethostname()
    case = f"ITC-{now:%Y%m%d-%H%M}-{hashlib.sha1((host + now.isoformat()).encode()).hexdigest()[:4].upper()}"
    return {
        "case_id": case,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "host": host,
        "elevated": admin,
        "score": score,
        "grade": grade_for(score),
        "score_capped_by_critical": capped,
        "coverage": {"evaluated": evaluated, "total": len(findings),
                     "percent": round(100 * evaluated / len(findings)) if findings else 0},
        "counts": counts,
        "top_risks": [{"id": f["id"], "title": f["title"], "severity": f["severity"], "status": f["status"],
                       "actual": f["actual"]} for f in risks[:5]],
        "findings": findings,
    }


def run_security_scan(
    progress: Callable[[dict, int, int], None] | None = None,
    *,
    reg=None,
    ps_data: dict | None = None,
    admin: bool | None = None,
    signatures: Callable[[list[str]], Any] | None = None,
    listeners: Callable[[], Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """
    Run all checks. `progress(finding, index, total)` fires after each check —
    the GUI uses it to animate the live scan sequence. Keyword args exist so the
    module is fully testable without Windows.
    """
    reg = reg or WinRegistry()
    admin = is_admin() if admin is None else admin
    now = now or datetime.now()
    ps = ps_data if ps_data is not None else collect_ps(admin)
    ctx = Ctx(reg, ps, admin, signatures or check_signatures, listeners or collect_listeners, now)

    findings: list[dict] = []
    total = len(CHECKS)
    for i, (cid, fn) in enumerate(CHECKS, 1):
        try:
            res = fn(ctx)
        except Exception as e:  # noqa: BLE001 — one broken check must not kill the scan
            res = ("UNKNOWN", "Check failed", f"{type(e).__name__}: {e}")
        f = _build(cid, *res)
        findings.append(f)
        if progress:
            try:
                progress(f, i, total)
            except Exception:  # noqa: BLE001
                pass
    return summarize(findings, admin, now)


def format_text(result: dict) -> str:
    """Plain-text summary for dev/debug only (the product UI never shows this)."""
    lines = [
        f"CASE {result['case_id']}  {result['timestamp']}  host={result['host']}  elevated={result['elevated']}",
        f"SCORE {result['score']}/100 ({result['grade']})  coverage {result['coverage']['evaluated']}/{result['coverage']['total']}"
        + ("  [capped by CRITICAL failure]" if result["score_capped_by_critical"] else ""),
        "",
    ]
    for f in result["findings"]:
        lines.append(f"[{f['status']:<11}] {f['severity']:<8} {f['id']}  {f['title']}  ->  {f['actual']}")
    return "\n".join(lines)


if __name__ == "__main__":  # dev only: python -m modules.security  (shows a console by design)
    print(format_text(run_security_scan(progress=lambda f, i, n: print(f"  {i}/{n} {f['id']} {f['status']}"))))
