from modules.inventory import get_inventory
from modules.network import get_network_info
from modules.processes import get_top_processes

from modules.health import calculate_health
from modules.root_cause import analyze_root_cause
from modules.fix_plan import generate_fix_plan
from modules.fix_engine import run_auto_fixes
from modules.history import load_previous_report, compare_reports, save_report
from modules.export import export_report

from modules.formatter import print_inventory


data = {}

# =====================
# Data Collection Layer
# =====================

inventory = get_inventory()

data["system"] = inventory["system"]
data["cpu"] = inventory["cpu"]
data["ram"] = inventory["ram"]
data["disk"] = inventory["disk"]

data["network"] = get_network_info()
data["processes"] = get_top_processes()

# =====================
# Analysis Layer
# =====================

data["health"] = calculate_health(
    data["cpu"],
    data["ram"],
    data["disk"]
)

data["root_cause"] = analyze_root_cause(data)

data["fix_plan"] = generate_fix_plan(
    data["root_cause"]
)

# =====================
# Auto-Fix Layer
# =====================

data["auto_fixes"] = run_auto_fixes(data["root_cause"])

# =====================
# History Layer
# =====================

previous = load_previous_report()
data["changes"] = compare_reports(data, previous)
save_report(data)

# =====================
# Export Layer
# =====================

data["export"] = export_report(data)

# =====================
# Presentation Layer
# =====================

print_inventory(data)
