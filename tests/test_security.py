import os, tempfile, unittest
from datetime import datetime

from modules import security as S
from modules import security_fix as SF


class FakeReg:
    def __init__(self, values=None, keys=None, runs=None):
        self.v = dict(values or {})
        self.keys = set(keys or [])
        self.runs = dict(runs or {})  # (hive,path) -> {name: cmd}

    def get(self, hive, path, name):
        return self.v.get((hive, path, name))

    def key_exists(self, hive, path):
        return (hive, path) in self.keys

    def list_values(self, hive, path):
        return dict(self.runs.get((hive, path), {}))

    def set_dword(self, hive, path, name, value):
        self.v[(hive, path, name)] = int(value)

    def delete_value(self, hive, path, name):
        self.v.pop((hive, path, name), None)


NOW = datetime(2026, 11, 15, 12, 0)
FW = S._FW_BASE
TS, RDP = S._TS, S._RDP_TCP
POLSYS = S._POL_SYS


def hardened_reg():
    v = {}
    for k in ("DomainProfile", "StandardProfile", "PublicProfile"):
        v[("HKLM", f"{FW}\\{k}", "EnableFirewall")] = 1
    v[("HKLM", TS, "fDenyTSConnections")] = 1
    v[("HKLM", S._SMB, "SMB1")] = 0
    v[("HKLM", r"SOFTWARE\Policies\Microsoft\Windows NT\DNSClient", "EnableMulticast")] = 0
    v[("HKLM", r"SYSTEM\CurrentControlSet\Control\SecureBoot\State", "UEFISecureBootEnabled")] = 1
    v[("HKLM", POLSYS, "EnableLUA")] = 1
    v[("HKLM", POLSYS, "ConsentPromptBehaviorAdmin")] = 5
    v[("HKLM", POLSYS, "InactivityTimeoutSecs")] = 600
    v[("HKLM", r"SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest", "UseLogonCredential")] = 0
    v[("HKLM", r"SYSTEM\CurrentControlSet\Control\Lsa", "RunAsPPL")] = 1
    v[("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging", "EnableScriptBlockLogging")] = 1
    return FakeReg(v)


GOOD_PS = {
    "defender": {"ok": True, "rtp": True, "sigAge": 1, "tamper": True},
    "av": ["Windows Defender"],
    "admins": ["PC\\Admin2"],
    "users": [{"sid": "S-1-5-21-1-500", "name": "Administrator", "enabled": False},
              {"sid": "S-1-5-21-1-501", "name": "Guest", "enabled": False}],
    "lastHotfix": "2026-11-05",
    "bitlocker": 1,
    "exclusions": [],
}


def scan(reg, ps, admin=True, sigs=None, listeners=None):
    return S.run_security_scan(
        reg=reg, ps_data=ps, admin=admin, now=NOW,
        signatures=lambda p: {} if sigs is None else sigs,
        listeners=lambda: [] if listeners is None else listeners,
    )


def by_id(res, cid):
    return next(f for f in res["findings"] if f["id"] == cid)


class TestScan(unittest.TestCase):
    def test_hardened_machine_scores_100(self):
        r = scan(hardened_reg(), GOOD_PS)
        self.assertEqual(r["score"], 100, [ (f["id"], f["status"], f["actual"]) for f in r["findings"] if f["status"] != "PASS"])
        self.assertEqual(r["grade"], "A")
        self.assertEqual(r["coverage"]["percent"], 100)

    def test_progress_fires_once_per_check(self):
        seen = []
        S.run_security_scan(progress=lambda f, i, n: seen.append((f["id"], i, n)), reg=hardened_reg(),
                            ps_data=GOOD_PS, admin=True, now=NOW,
                            signatures=lambda p: {}, listeners=lambda: [])
        self.assertEqual(len(seen), len(S.CHECKS))
        self.assertEqual(seen[-1][1], seen[-1][2])

    def test_critical_failure_caps_score(self):
        reg = hardened_reg()
        reg.v[("HKLM", r"SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest", "UseLogonCredential")] = 1
        r = scan(reg, GOOD_PS)
        self.assertEqual(by_id(r, "ITC-040")["status"], "FAIL")
        self.assertLessEqual(r["score"], 59)
        self.assertTrue(r["score_capped_by_critical"])
        self.assertEqual(r["grade"], "F")
        self.assertEqual(r["top_risks"][0]["id"], "ITC-040")

    def test_bad_machine(self):
        ps = dict(GOOD_PS, defender={"ok": True, "rtp": False, "sigAge": 40, "tamper": False}, av=["Windows Defender"],
                  admins=["a", "b", "c", "d", "e"], lastHotfix="2026-05-01", bitlocker=0)
        reg = FakeReg({("HKLM", TS, "fDenyTSConnections"): 0, ("HKLM", RDP, "UserAuthentication"): 0,
                       ("HKLM", S._SMB, "SMB1"): 1,
                       ("HKLM", f"{FW}\\PublicProfile", "EnableFirewall"): 0})
        r = scan(reg, ps, listeners=[{"ip": "0.0.0.0", "port": 23, "pid": 4, "process": "telnetd.exe"}])
        for cid in ("ITC-001", "ITC-002", "ITC-010", "ITC-011", "ITC-012", "ITC-014", "ITC-020", "ITC-031", "ITC-050"):
            self.assertEqual(by_id(r, cid)["status"], "FAIL", cid)
        self.assertLess(r["score"], 40)

    def test_third_party_av_is_warn_not_fail(self):
        ps = dict(GOOD_PS, defender={"ok": True, "rtp": False, "sigAge": 99, "tamper": True}, av=["Windows Defender", "ESET Endpoint"])
        r = scan(hardened_reg(), ps)
        self.assertEqual(by_id(r, "ITC-001")["status"], "WARN")
        self.assertEqual(by_id(r, "ITC-002")["status"], "UNKNOWN")  # stale defender sigs must not count

    def test_non_admin_marks_needs_admin_and_lowers_coverage(self):
        r = scan(hardened_reg(), GOOD_PS, admin=False)
        self.assertEqual(by_id(r, "ITC-004")["status"], "NEEDS_ADMIN")
        self.assertLess(r["coverage"]["percent"], 100)
        self.assertEqual(r["score"], 100)  # unevaluated checks never punish

    def test_ps_failure_degrades_to_unknown_not_crash(self):
        r = scan(hardened_reg(), {"_error": "powershell rc=1"})
        self.assertEqual(by_id(r, "ITC-001")["status"], "UNKNOWN")
        self.assertIsNotNone(r["score"])

    def test_broken_check_is_isolated(self):
        class Boom(FakeReg):
            def get(self, *a):
                raise RuntimeError("registry exploded")
        r = scan(Boom(), GOOD_PS)
        self.assertEqual(by_id(r, "ITC-010")["status"], "UNKNOWN")
        self.assertEqual(len(r["findings"]), len(S.CHECKS))

    def test_startup_unsigned_in_downloads_fails(self):
        runs = {("HKCU", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"): {
            "Updater": r'"C:\Users\x\Downloads\upd.exe" /silent',
            "Teams": r'"C:\Program Files\Teams\teams.exe"'}}
        reg = hardened_reg(); reg.runs = runs
        sigs = {r"C:\Users\x\Downloads\upd.exe": {"status": "NotSigned"},
                r"C:\Program Files\Teams\teams.exe": {"status": "Valid"}}
        f = by_id(scan(reg, GOOD_PS, sigs=sigs), "ITC-060")
        self.assertEqual(f["status"], "FAIL")
        self.assertIn("Updater", f["actual"])

    def test_startup_signed_ok_and_sig_unavailable_is_heuristic(self):
        runs = {("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"): {"AV": r"C:\Program Files\AV\av.exe -bg"}}
        reg = hardened_reg(); reg.runs = runs
        f = by_id(scan(reg, GOOD_PS, sigs={r"C:\Program Files\AV\av.exe": {"status": "Valid"}}), "ITC-060")
        self.assertEqual(f["status"], "PASS")
        r2 = S.run_security_scan(reg=reg, ps_data=GOOD_PS, admin=True, now=NOW,
                                 signatures=lambda p: None, listeners=lambda: [])
        self.assertIn("unavailable", by_id(r2, "ITC-060")["evidence"])

    def test_parse_command_path(self):
        self.assertEqual(S.parse_command_path('"C:\\A B\\x.exe" -k'), "C:\\A B\\x.exe")
        self.assertEqual(S.parse_command_path(r"C:\Program Files\X\y.exe /s"), r"C:\Program Files\X\y.exe")
        self.assertEqual(S.parse_command_path("garbage"), "")

    def test_fingerprint_stable_and_changes_with_state(self):
        a = by_id(scan(hardened_reg(), GOOD_PS), "ITC-010")["fingerprint"]
        b = by_id(scan(hardened_reg(), GOOD_PS), "ITC-010")["fingerprint"]
        self.assertEqual(a, b)
        reg = hardened_reg(); reg.v[("HKLM", f"{FW}\\PublicProfile", "EnableFirewall")] = 0
        self.assertNotEqual(a, by_id(scan(reg, GOOD_PS), "ITC-010")["fingerprint"])

    def test_catalog_integrity(self):
        ids = [c for c, _ in S.CHECKS]
        self.assertEqual(len(ids), len(set(ids)))
        for cid in ids:
            m = S.CATALOG[cid]
            self.assertIn(m["severity"], S.SEV_WEIGHT)
            self.assertTrue(m["remediation"] and m["expected"] and m["framework_area"])


class TestFix(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.jp = os.path.join(self.tmp, "j.jsonl")
        self.reg = hardened_reg()
        self.reg.v[("HKLM", r"SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest", "UseLogonCredential")] = 1
        r = scan(self.reg, GOOD_PS)
        self.finding = by_id(r, "ITC-040")
        self.key = ("HKLM", r"SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest", "UseLogonCredential")

    def test_dry_run_is_default_and_changes_nothing(self):
        res = SF.apply_fix(self.finding, reg=self.reg, admin=True, journal_path=self.jp)
        self.assertEqual(res["status"], "DRY_RUN")
        self.assertEqual(self.reg.v[self.key], 1)
        self.assertFalse(os.path.exists(self.jp))

    def test_needs_admin(self):
        res = SF.apply_fix(self.finding, dry_run=False, reg=self.reg, admin=False, journal_path=self.jp)
        self.assertEqual(res["status"], "NEEDS_ADMIN")
        self.assertEqual(self.reg.v[self.key], 1)

    def test_apply_then_rollback_restores(self):
        res = SF.apply_fix(self.finding, dry_run=False, reg=self.reg, admin=True, journal_path=self.jp)
        self.assertEqual(res["status"], "APPLIED")
        self.assertEqual(self.reg.v[self.key], 0)
        rb = SF.rollback(res["entry_id"], reg=self.reg, admin=True, journal_path=self.jp)
        self.assertEqual(rb["status"], "ROLLED_BACK")
        self.assertEqual(self.reg.v[self.key], 1)
        self.assertTrue(SF.list_journal(self.jp)[0]["undone"])
        self.assertEqual(SF.rollback(res["entry_id"], reg=self.reg, admin=True, journal_path=self.jp)["status"], "ALREADY_UNDONE")

    def test_rollback_deletes_when_value_was_absent(self):
        reg = hardened_reg()
        key = ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging", "EnableScriptBlockLogging")
        del reg.v[key]
        f = by_id(scan(reg, GOOD_PS), "ITC-061")
        res = SF.apply_fix(f, dry_run=False, reg=reg, admin=True, journal_path=self.jp)
        self.assertEqual(reg.v[key], 1)
        SF.rollback(res["entry_id"], reg=reg, admin=True, journal_path=self.jp)
        self.assertNotIn(key, reg.v)

    def test_refuses_non_dword_and_no_fix(self):
        reg = hardened_reg(); reg.v[self.key] = "1"
        res = SF.apply_fix(self.finding, dry_run=False, reg=reg, admin=True, journal_path=self.jp)
        self.assertEqual(res["status"], "UNEXPECTED_TYPE")
        passing = by_id(scan(hardened_reg(), GOOD_PS), "ITC-010")
        self.assertEqual(SF.apply_fix(passing, reg=reg, admin=True)["status"], "NO_FIX")


if __name__ == "__main__":
    unittest.main()
