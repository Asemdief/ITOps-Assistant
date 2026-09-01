def analyze_root_cause(data):
    """
    Analyze collected data and identify root causes with specific disk issues.
    """
    issues = []
    suggestions = []

    # ================= RAM =================
    if data["ram"]["usage_percent"] > 75:
        issues.append("High RAM usage")
        suggestions.append("Close memory intensive applications")

    # ================= DISK =================
    for disk in data["disk"]:
        usage = disk["usage_percent"]
        drive = disk["device"]

        if usage >= 95:
            issues.append(f"Critical disk space on {drive}")
            suggestions.append(
                f"Immediately free space on {drive} (delete large files or move data)"
            )
        elif usage >= 85:
            issues.append(f"High disk usage on {drive}")
            suggestions.append(
                f"Clean temporary files and large folders on {drive}"
            )
        elif usage >= 70:
            issues.append(f"Elevated disk usage on {drive}")
            suggestions.append(
                f"Monitor free space on {drive} and remove unused files"
            )

    # ================= NETWORK =================
    network = data["network"]

    if not network["internet_ok"]:
        issues.append("Internet connectivity issue")
        suggestions.append("Check ISP or physical connection")
    elif not network["dns_ok"]:
        issues.append("DNS resolution issue")
        suggestions.append("Check DNS server settings")
    elif not network["gateway_ok"]:
        issues.append("Gateway unreachable")
        suggestions.append("Check switch port or router")

    # ================= STATUS =================
    if len(issues) == 0:
        status = "Healthy"
    elif len(issues) == 1:
        status = "Minor Issues"
    else:
        status = "Multiple Issues Detected"

    return {
        "status": status,
        "issues": issues,
        "suggestions": suggestions
    }
