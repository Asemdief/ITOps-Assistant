"""Generate prioritized fix plan from root cause."""

from __future__ import annotations


def generate_fix_plan(root_cause: dict) -> list[dict]:
    issues = root_cause.get("issues") or []
    suggestions = root_cause.get("suggestions") or []
    plan: list[dict] = []

    for i, issue in enumerate(issues):
        low = issue.lower()
        if "internet" in low or "gateway" in low or "dns" in low:
            priority = "HIGH"
            fix = suggestions[i] if i < len(suggestions) else "Check network connectivity"
            if "internet" in low:
                fix = "Check ISP, physical connection, or router status"
        elif "high disk" in low:
            priority = "MEDIUM"
            fix = suggestions[i] if i < len(suggestions) else "Free disk space"
            if "d:\\" in low or "d:" in low:
                fix = "Clean temporary files, Downloads, and Recycle Bin on D:\\."
            elif "e:\\" in low or "e:" in low:
                fix = "Monitor free space on E:\\ and remove unused files regularly."
        elif "elevated disk" in low:
            priority = "LOW"
            fix = suggestions[i] if i < len(suggestions) else "Monitor disk space"
        elif "cpu" in low or "memory" in low:
            priority = "MEDIUM"
            fix = suggestions[i] if i < len(suggestions) else "Reduce load"
        else:
            priority = "LOW"
            fix = suggestions[i] if i < len(suggestions) else "Review system status"
        plan.append({"priority": priority, "issue": issue, "fix": fix})

    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    plan.sort(key=lambda x: order.get(x["priority"], 9))
    return plan
