def generate_fix_plan(root_cause):
    """
    Generate prioritized fix plan based on detected issues.
    """
    fixes = []

    for issue in root_cause["issues"]:

        # ---------- RAM ----------
        if issue == "High RAM usage":
            fixes.append({
                "priority": "MEDIUM",
                "issue": issue,
                "fix": "Close high memory consuming processes"
            })

        # ---------- DISK ----------
        elif issue.startswith("Critical disk space on"):
            drive = issue.split("on ")[-1]
            fixes.append({
                "priority": "HIGH",
                "issue": issue,
                "fix": f"Immediately free space on {drive}. Delete large files or move data to another drive."
            })

        elif issue.startswith("High disk usage on"):
            drive = issue.split("on ")[-1]
            fixes.append({
                "priority": "MEDIUM",
                "issue": issue,
                "fix": f"Clean temporary files, Downloads, and Recycle Bin on {drive}."
            })

        elif issue.startswith("Elevated disk usage on"):
            drive = issue.split("on ")[-1]
            fixes.append({
                "priority": "LOW",
                "issue": issue,
                "fix": f"Monitor free space on {drive} and remove unused files regularly."
            })

        # ---------- NETWORK ----------
        elif issue == "Internet connectivity issue":
            fixes.append({
                "priority": "HIGH",
                "issue": issue,
                "fix": "Check ISP, physical connection, or router status"
            })

        elif issue == "DNS resolution issue":
            fixes.append({
                "priority": "HIGH",
                "issue": issue,
                "fix": "Flush DNS cache (ipconfig /flushdns) and try public DNS (8.8.8.8)"
            })

        elif issue == "Gateway unreachable":
            fixes.append({
                "priority": "HIGH",
                "issue": issue,
                "fix": "Check gateway, switch port, or DHCP settings"
            })

    # Sort by priority (HIGH → MEDIUM → LOW)
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    fixes.sort(key=lambda x: priority_order.get(x["priority"], 99))

    return fixes
