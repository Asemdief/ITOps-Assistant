# Security Posture Module (v1.10)

Files: `modules/security.py` (22 read-only checks + scoring), `modules/security_fix.py`
(opt-in reversible fixes + journal), `modules/registry_io.py` (winreg layer),
`tests/test_security.py` (18 tests: `python -m unittest tests.test_security -v`).

## Rules
- Scan is READ-ONLY. Fixes are opt-in: dry-run default, journal, rollback.
- Locale-independent: winreg + ONE batched PowerShell call returning JSON; SIDs, not names.
- Cannot evaluate => UNKNOWN / NEEDS_ADMIN: excluded from score, lowers *coverage*. Never guessed.
- Score = severity-weighted (CRITICAL 10, HIGH 6, MEDIUM 3, LOW 1; WARN = half). Any CRITICAL FAIL caps score at 59.
- `framework_area` is a plain-language area label, NOT an official CIS control ID.

## API
    from modules.security import run_security_scan
    result = run_security_scan(progress=lambda finding, i, n: ...)   # drives the live scan animation
    # result: case_id, score, grade, coverage, counts, top_risks, findings[]
    from modules.security_fix import apply_fix, rollback, list_journal
    apply_fix(finding)                 # dry-run preview
    apply_fix(finding, dry_run=False)  # applies + journals (needs admin for HKLM)

## NOT verified on real Windows yet (test on Win10 + Win11, admin + standard, Arabic locale)
1. PowerShell batch (Get-MpComputerStatus, Get-LocalGroupMember -SID, Get-HotFix) output/timing.
2. BitLocker via Shell `System.Volume.BitLockerProtection` — value mapping (1=on, 0=off) must be confirmed.
3. SMB1 / Secure Boot registry semantics across Windows builds.
4. Scan time: Get-HotFix can take several seconds — run security in parallel with network probes.
