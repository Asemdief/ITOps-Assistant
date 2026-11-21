"""Health score calculation."""

from __future__ import annotations


def calculate_health(cpu: dict, ram: dict, disk: list) -> dict:
    score = 100
    recommendations: list[str] = []

    cu = float(cpu.get("usage_percent") or 0)
    if cu >= 90:
        score -= 20
        recommendations.append("CPU usage is critically high.")
    elif cu >= 70:
        score -= 10
        recommendations.append("CPU usage is above normal.")

    ru = float(ram.get("usage_percent") or 0)
    if ru >= 90:
        score -= 20
        recommendations.append("Memory usage is critically high.")
    elif ru >= 75:
        score -= 10
        recommendations.append("Memory usage is elevated.")

    for d in disk or []:
        pct = float(d.get("usage_percent") or 0)
        dev = d.get("device", "Drive")
        if pct >= 95:
            score -= 18
            recommendations.append(f"{dev} is critically full ({pct}%). Free space urgently.")
        elif pct >= 85:
            score -= 12
            recommendations.append(
                f"{dev} is highly used ({pct}%). Clean temporary files and large folders."
            )
        elif pct >= 70:
            score -= 6
            recommendations.append(f"{dev} is above 70% usage ({pct}%). Monitor free space.")

    score = max(0, min(100, score))
    if score >= 90:
        status = "Excellent"
    elif score >= 75:
        status = "Good"
    elif score >= 60:
        status = "Warning"
    else:
        status = "Critical"

    return {"score": score, "status": status, "recommendations": recommendations}
