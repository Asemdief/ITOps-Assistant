import psutil


def get_disk_info():
    """
    Collect disk usage information with clearer status levels.
    """
    disks = []

    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            used_percent = usage.percent

            if used_percent < 70:
                status = "Healthy"
            elif used_percent < 85:
                status = "Warning"
            elif used_percent < 95:
                status = "High"
            else:
                status = "Critical"

            disks.append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "filesystem": partition.fstype,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "usage_percent": used_percent,
                "status": status
            })

        except (PermissionError, OSError):
            continue

    return disks
