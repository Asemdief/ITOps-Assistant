def get_top_cpu(processes, limit=10):

    return sorted(
        processes,
        key=lambda x: x["cpu"],
        reverse=True
    )[:limit]


def get_top_ram(processes, limit=10):

    return sorted(
        processes,
        key=lambda x: x["ram"],
        reverse=True
    )[:limit]