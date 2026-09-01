def calculate_health(cpu, ram, disk):
    """
    Calculate overall system health score and generate specific recommendations.
    """
    score = 100
    recommendations = []

    # ---------- CPU ----------
    cpu_usage = cpu["usage_percent"]

    if cpu_usage > 90:
        score -= 25
        recommendations.append("CPU usage is extremely high.")
    elif cpu_usage > 70:
        score -= 15
        recommendations.append("CPU usage is above normal.")

    # ---------- RAM ----------
    ram_usage = ram["usage_percent"]

    if ram_usage > 90:
        score -= 25
        recommendations.append("RAM usage is critically high.")
    elif ram_usage > 75:
        score -= 15
        recommendations.append("RAM usage is high.")

    # ---------- DISK ----------
    if disk:
        for partition in disk:
            usage = partition["usage_percent"]
            drive = partition["device"]

            if usage >= 95:
                score -= 25
                recommendations.append(
                    f"{drive} is critically full ({usage}%). Free space immediately."
                )
            elif usage >= 85:
                score -= 15
                recommendations.append(
                    f"{drive} is highly used ({usage}%). Clean temporary files and large folders."
                )
            elif usage >= 70:
                score -= 8
                recommendations.append(
                    f"{drive} is above 70% usage ({usage}%). Monitor free space."
                )

    score = max(score, 0)

    if score >= 90:
        status = "Excellent"
    elif score >= 75:
        status = "Good"
    elif score >= 60:
        status = "Warning"
    else:
        status = "Critical"

    return {
        "score": score,
        "status": status,
        "recommendations": recommendations
    }
