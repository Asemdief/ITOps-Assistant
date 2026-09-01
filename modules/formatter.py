def print_inventory(data):

    system = data["system"]
    cpu = data["cpu"]
    ram = data["ram"]
    disks = data["disk"]
    health = data["health"]
    network = data["network"]
    root_cause = data["root_cause"]
    fix_plan = data["fix_plan"]
    processes = data["processes"]
    changes = data.get("changes", [])
    auto_fixes = data.get("auto_fixes", [])
    export_info = data.get("export", {})

    print("\n" + "=" * 50)
    print("          ITOps Assistant Report")
    print("=" * 50)

    # ================= SYSTEM =================
    print("\n🖥 SYSTEM")
    print(f"Computer Name : {system['computer_name']}")
    print(f"User          : {system['username']}")
    print(
        f"OS            : "
        f"{system['os']['name']} "
        f"{system['os']['release']}"
    )

    # ================= CPU =================
    print("\n⚙️ CPU")
    print(f"Name          : {cpu['name']}")
    print(f"Cores         : {cpu['physical_cores']}")
    print(f"Threads       : {cpu['logical_cores']}")
    print(f"Usage         : {cpu['usage_percent']}%")

    # ================= RAM =================
    print("\n🧠 RAM")
    print(f"Total         : {ram['total_gb']} GB")
    print(f"Available     : {ram['available_gb']} GB")
    print(f"Usage         : {ram['usage_percent']}%")

    # ================= DISKS =================
    print("\n💾 DISKS")

    for disk in disks:
        print("\n" + "-" * 40)
        print(f"Drive         : {disk['device']}")
        print(f"File System   : {disk['filesystem']}")
        print(f"Total         : {disk['total_gb']} GB")
        print(f"Used          : {disk['used_gb']} GB")
        print(f"Free          : {disk['free_gb']} GB")
        print(f"Usage         : {disk['usage_percent']}%")
        print(f"Status        : {disk['status']}")

    # ================= HEALTH =================
    print("\n📊 HEALTH")
    print(f"Score         : {health['score']}/100")
    print(f"Status        : {health['status']}")

    # ================= RECOMMENDATIONS =================
    if health["recommendations"]:
        print("\n💡 RECOMMENDATIONS")
        for rec in health["recommendations"]:
            print(f"- {rec}")

    # ================= NETWORK =================
    print("\n🌐 NETWORK DIAGNOSTICS")
    print(f"Adapter       : {network['adapter']}")
    print(f"IP Address    : {network['ip']}")
    print(f"Gateway       : {network['gateway']}")
    print(f"MAC Address   : {network['mac']}")

    print("\n🔍 TESTS")
    print(f"Gateway       : {'✔' if network['gateway_ok'] else '❌'}")
    print(f"DNS           : {'✔' if network['dns_ok'] else '❌'}")
    print(f"Internet      : {'✔' if network['internet_ok'] else '❌'}")

    # Latency section
    gw_lat = network.get("gateway_latency", {})
    net_lat = network.get("internet_latency", {})

    print("\n📶 LATENCY")
    if gw_lat.get("avg_ms") is not None:
        print(f"Gateway       : {gw_lat['avg_ms']:.0f} ms   (Loss: {gw_lat['loss_percent']:.0f}%)")
    else:
        print("Gateway       : N/A")

    if net_lat.get("avg_ms") is not None:
        print(f"Internet      : {net_lat['avg_ms']:.0f} ms   (Loss: {net_lat['loss_percent']:.0f}%)")
    else:
        print("Internet      : N/A")

    print(f"\nStatus        : {network['status']}")

    # ================= ROOT CAUSE =================
    print("\n🧠 ROOT CAUSE ANALYSIS")
    print(f"Status        : {root_cause['status']}")

    if root_cause["issues"]:
        print("\nIssues:")
        for issue in root_cause["issues"]:
            print(f"- {issue}")

    if root_cause["suggestions"]:
        print("\nSuggestions:")
        for suggestion in root_cause["suggestions"]:
            print(f"- {suggestion}")

    # ================= FIX PLAN =================
    print("\n🛠 FIX PLAN")

    if not fix_plan:
        print("- No fixes required")
    else:
        for fix in fix_plan:
            print(f"\n[{fix['priority']}]")
            print(f"Issue         : {fix['issue']}")
            print(f"Fix           : {fix['fix']}")

    # ================= AUTO FIXES =================
    print("\n⚙️ AUTO FIXES EXECUTED")

    if not auto_fixes:
        print("- No automatic fixes were needed")
    else:
        for fix in auto_fixes:
            status = "✔" if fix.get("success") else "❌"
            print(f"{status} {fix.get('action')}")
            if fix.get("details"):
                print(f"   → {fix['details']}")

    # ================= TOP PROCESSES =================
    print("\n📋 PROCESS ANALYSIS")

    # Warnings first (if any)
    warnings = processes.get("warnings", [])
    if warnings:
        print("\n⚠️  HIGH RESOURCE WARNINGS")
        print("-" * 50)
        for w in warnings:
            print(f"- {w}")

    print("\n🔥 TOP CPU PROCESSES")
    print("-" * 55)
    print(f"{'Process':<28} {'CPU':>8} {'RAM':>8}")
    print("-" * 55)

    for process in processes["top_cpu"]:
        name = process["name"]
        if len(name) > 26:
            name = name[:23] + "..."
        flag = " ⚠" if process.get("high_cpu") else ""
        print(
            f"{name:<28}"
            f"{process['cpu_percent']:>7.1f}% "
            f"{process['memory_percent']:>7.2f}%{flag}"
        )

    print("\n🧠 TOP RAM PROCESSES")
    print("-" * 55)
    print(f"{'Process':<28} {'RAM':>8} {'CPU':>8}")
    print("-" * 55)

    for process in processes["top_ram"]:
        name = process["name"]
        if len(name) > 26:
            name = name[:23] + "..."
        flag = " ⚠" if process.get("high_ram") else ""
        print(
            f"{name:<28}"
            f"{process['memory_percent']:>7.2f}% "
            f"{process['cpu_percent']:>7.1f}%{flag}"
        )

    # ================= HISTORY / CHANGES =================
    if changes:
        print("\n📈 CHANGES SINCE LAST RUN")
        print("-" * 50)
        for change in changes:
            print(f"- {change}")
    else:
        print("\n📈 CHANGES SINCE LAST RUN")
        print("-" * 50)
        print("- No previous report found (or no significant changes)")

    # ================= EXPORT =================
    export_info = data.get("export", {})
    if export_info:
        print("\n📁 EXPORTED REPORTS")
        print("-" * 50)
        if export_info.get("json"):
            print(f"JSON : {export_info['json']}")
        if export_info.get("html"):
            print(f"HTML : {export_info['html']}")
