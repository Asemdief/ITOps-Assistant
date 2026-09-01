import psutil
import socket
import subprocess
import re
import ipaddress


# Common Virtual MAC OUI prefixes (first 3 bytes)
VIRTUAL_MAC_PREFIXES = {
    "0A:00:27",   # VirtualBox
    "08:00:27",   # VirtualBox
    "00:50:56",   # VMware
    "00:0C:29",   # VMware
    "00:05:69",   # VMware
    "00:1C:42",   # Parallels
    "00:15:5D",   # Hyper-V
    "00:03:FF",   # Microsoft Virtual
    "52:54:00",   # QEMU/KVM
    "00:16:3E",   # Xen
}


VIRTUAL_NAME_KEYWORDS = (
    "virtual",
    "vmware",
    "virtualbox",
    "vbox",
    "hyper-v",
    "vethernet",
    "loopback",
    "vpn",
    "tunnel",
    "bluetooth",
    "npcap",
    "host-only",
    "host only",
    "docker",
    "wsl",
    "tap-",
    "tun-",
)


def is_virtual_adapter(name: str, mac: str | None) -> bool:
    """Check if adapter is virtual by name or MAC OUI."""
    name_lower = name.lower()

    if any(kw in name_lower for kw in VIRTUAL_NAME_KEYWORDS):
        return True

    if mac:
        # Normalize MAC to uppercase with colons
        mac_norm = mac.upper().replace("-", ":")
        prefix = ":".join(mac_norm.split(":")[:3])
        if prefix in VIRTUAL_MAC_PREFIXES:
            return True

    return False


def get_adapter_details():
    """
    Collect all active IPv4 network adapters.
    """
    interfaces = psutil.net_if_addrs()
    stats = psutil.net_if_stats()

    adapters = []

    for name, addrs in interfaces.items():
        if name not in stats:
            continue

        stat = stats[name]
        if not stat.isup:
            continue

        ipv4 = None
        mac = None
        netmask = None

        for addr in addrs:
            if addr.family == socket.AF_INET:
                ipv4 = addr.address
                netmask = addr.netmask
            elif addr.family == psutil.AF_LINK:
                mac = addr.address

        if not ipv4:
            continue

        # Ignore APIPA and loopback
        if ipv4.startswith("169.254.") or ipv4.startswith("127."):
            continue

        adapters.append({
            "name": name,
            "ip": ipv4,
            "netmask": netmask,
            "mac": mac,
            "is_virtual": is_virtual_adapter(name, mac)
        })

    return adapters


def get_default_gateway():
    """
    Get the best default gateway from Windows routing table.
    Prefers the route with the lowest metric when multiple exist.
    Returns: (gateway, interface_ip) or (None, None)
    """
    try:
        output = subprocess.check_output(
            ["route", "print", "-4"],
            text=True,
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
            errors="ignore"
        )

        candidates = []

        for line in output.splitlines():
            line = line.strip()

            # Default route lines look like:
            # 0.0.0.0  0.0.0.0  <gateway>  <interface>  <metric>
            if not line.startswith("0.0.0.0"):
                continue

            parts = re.split(r"\s+", line)
            if len(parts) < 4:
                continue

            gateway = parts[2]
            interface_ip = parts[3]

            # Skip invalid
            if gateway == "0.0.0.0" or gateway.startswith("127."):
                continue

            # Metric is usually the last column
            metric = 9999
            if len(parts) >= 5 and parts[-1].isdigit():
                metric = int(parts[-1])

            candidates.append((metric, gateway, interface_ip))

        if candidates:
            # Sort by metric (lowest = preferred)
            candidates.sort(key=lambda x: x[0])
            _, gateway, interface_ip = candidates[0]
            return gateway, interface_ip

    except (subprocess.CalledProcessError, OSError, ValueError):
        pass

    return None, None


def same_subnet(ip1: str, ip2: str, netmask: str | None = None) -> bool:
    """Check if two IPs are in the same subnet."""
    try:
        if netmask:
            network = ipaddress.IPv4Network(f"{ip1}/{netmask}", strict=False)
            return ipaddress.IPv4Address(ip2) in network
        # Fallback: assume /24
        return ip1.rsplit(".", 1)[0] == ip2.rsplit(".", 1)[0]
    except (ValueError, ipaddress.AddressValueError):
        return False


def get_active_adapter():
    """
    Identify the real active adapter used for internet traffic.
    Priority order:
      1. Exact match with interface IP from default route
      2. Non-virtual adapter in the same subnet as the gateway
      3. Any non-virtual adapter
      4. Fallback to first available
    """
    adapters = get_adapter_details()

    if not adapters:
        return None, None, None, None

    gateway, route_ip = get_default_gateway()

    # ---------- Priority 1: Exact match on route interface IP ----------
    if route_ip:
        for adapter in adapters:
            if adapter["ip"] == route_ip:
                return (
                    adapter["name"],
                    adapter["ip"],
                    adapter["mac"],
                    adapter["netmask"]
                )

    # ---------- Priority 2: Same subnet as gateway + non-virtual ----------
    if gateway:
        for adapter in adapters:
            if adapter["is_virtual"]:
                continue
            if same_subnet(adapter["ip"], gateway, adapter["netmask"]):
                return (
                    adapter["name"],
                    adapter["ip"],
                    adapter["mac"],
                    adapter["netmask"]
                )

    # ---------- Priority 3: Any non-virtual adapter ----------
    physical = [a for a in adapters if not a["is_virtual"]]
    if physical:
        adapter = physical[0]
        return (
            adapter["name"],
            adapter["ip"],
            adapter["mac"],
            adapter["netmask"]
        )

    # ---------- Priority 4: Last resort ----------
    adapter = adapters[0]
    return (
        adapter["name"],
        adapter["ip"],
        adapter["mac"],
        adapter["netmask"]
    )


def check_gateway(gateway):
    """Test connectivity to the default gateway."""
    if not gateway:
        return False

    try:
        subprocess.check_output(
            ["ping", "-n", "1", "-w", "1000", gateway],
            stderr=subprocess.DEVNULL
        )
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


def check_dns():
    """Test DNS resolution."""
    try:
        socket.gethostbyname("google.com")
        return True
    except socket.gaierror:
        return False


def check_internet():
    """Test actual Internet connectivity using a public IP."""
    try:
        subprocess.check_output(
            ["ping", "-n", "1", "-w", "1500", "8.8.8.8"],
            stderr=subprocess.DEVNULL
        )
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


def measure_latency(host, count=4, timeout_ms=1000):
    """
    Measure average latency and packet loss to a host using ping.
    Returns dict: {"avg_ms": float|None, "loss_percent": float, "reachable": bool}
    """
    if not host:
        return {"avg_ms": None, "loss_percent": 100.0, "reachable": False}

    try:
        output = subprocess.check_output(
            ["ping", "-n", str(count), "-w", str(timeout_ms), host],
            text=True,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="ignore"
        )

        # Parse packet loss (Windows: "Lost = X (Y% loss)")
        loss_match = re.search(r"Lost\s*=\s*\d+\s*\((\d+)%\s*loss\)", output, re.IGNORECASE)
        loss_percent = float(loss_match.group(1)) if loss_match else 0.0

        # Parse Average latency (Windows: "Average = XXms")
        avg_match = re.search(r"Average\s*=\s*(\d+)ms", output, re.IGNORECASE)
        avg_ms = float(avg_match.group(1)) if avg_match else None

        reachable = loss_percent < 100

        return {
            "avg_ms": avg_ms,
            "loss_percent": loss_percent,
            "reachable": reachable
        }

    except (subprocess.CalledProcessError, OSError):
        return {"avg_ms": None, "loss_percent": 100.0, "reachable": False}


def get_network_info():
    """
    Main Network Diagnostic function.
    Includes connectivity tests + latency measurements.
    """
    (
        adapter,
        ip,
        mac,
        netmask
    ) = get_active_adapter()

    gateway, route_ip = get_default_gateway()

    gateway_ok = check_gateway(gateway)
    dns_ok = check_dns()
    internet_ok = check_internet()

    # Latency measurements
    gateway_latency = measure_latency(gateway, count=4)
    internet_latency = measure_latency("8.8.8.8", count=4)

    # Status logic
    if not adapter:
        status = "No Active Network"
    elif not gateway:
        status = "No Gateway"
    elif not gateway_ok:
        status = "Gateway Unreachable"
    elif not dns_ok:
        status = "DNS Failure"
    elif not internet_ok:
        status = "Internet Unreachable"
    else:
        status = "Internet OK"

    return {
        "adapter": adapter,
        "ip": ip,
        "netmask": netmask,
        "mac": mac,
        "gateway": gateway,
        "gateway_ok": gateway_ok,
        "dns_ok": dns_ok,
        "internet_ok": internet_ok,
        "status": status,
        "gateway_latency": gateway_latency,
        "internet_latency": internet_latency
    }
