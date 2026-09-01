import os
import platform
import socket
import psutil

from cpuinfo import get_cpu_info

from modules.disk import get_disk_info
from modules.network import get_network_info
from modules.process_analyzer import get_process_info


def get_system_info():

    return {
        "computer_name": socket.gethostname(),
        "username": os.getlogin(),
        "os": {
            "name": platform.system(),
            "version": platform.version(),
            "release": platform.release()
        }
    }


def get_cpu_info_block():

    cpu = get_cpu_info()

    return {
        "name": cpu.get("brand_raw"),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "usage_percent": psutil.cpu_percent(interval=1)
    }


def get_ram_info():

    ram = psutil.virtual_memory()

    return {
        "total_gb": round(ram.total / (1024 ** 3), 2),
        "available_gb": round(ram.available / (1024 ** 3), 2),
        "usage_percent": ram.percent
    }


def get_inventory():

    return {
        "system": get_system_info(),
        "cpu": get_cpu_info_block(),
        "ram": get_ram_info(),
        "disk": get_disk_info(),
        "network": get_network_info(),
        "processes": get_process_info()
    }