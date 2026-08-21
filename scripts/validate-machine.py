#!/usr/bin/env python3

from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <machine>")
    sys.exit(1)

machine_name = sys.argv[1]

machine_file = ROOT / "machines" / machine_name / "machine.yaml"
userdata_file = ROOT / "generated" / machine_name / "user-data"
provision_file = ROOT / "generated" / machine_name / "provision.ipxe"

machine = yaml.safe_load(machine_file.read_text())
userdata = yaml.safe_load(userdata_file.read_text())

a = userdata["autoinstall"]

expected_serial = machine["hardware"]["os_disk"]["serial"]

disks = [
    item for item in a["storage"]["config"]
    if item.get("type") == "disk"
]

if len(disks) != 1:
    raise RuntimeError(
        f"Expected exactly one installation disk, found {len(disks)}"
    )

actual_serial = disks[0]["match"]["serial"]

if actual_serial != expected_serial:
    raise RuntimeError(
        f"Disk mismatch: machine={expected_serial}, autoinstall={actual_serial}"
    )

provision = provision_file.read_text()

if "autoinstall" not in provision:
    raise RuntimeError("provision.ipxe does not enable autoinstall")

if f"/pxe/{machine_name}/" not in provision:
    raise RuntimeError("Incorrect NoCloud configuration URL")

print("AI Forge validation: PASS")
print(f"Machine:       {machine['name']}")
print(f"Architecture:  {machine['architecture']}")
print(f"Hostname:      {a['identity']['hostname']}")
print(f"OS disk model: {machine['hardware']['os_disk']['model']}")
print(f"OS disk serial:{expected_serial}")
print("Disk wipe:     ENABLED")
print("Autoinstall:   ENABLED")
