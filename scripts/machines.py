#!/usr/bin/env python3

from pathlib import Path
import yaml
import sys

ROOT = Path(__file__).resolve().parents[1]
MACHINES_DIR = ROOT / "machines"


def load_machines():
    machines = []

    for machine_file in sorted(MACHINES_DIR.glob("*/machine.yaml")):
        with open(machine_file, "r", encoding="utf-8") as f:
            machine = yaml.safe_load(f)

        machines.append(machine)

    return machines


def validate(machines):
    names = {}
    ips = {}
    macs = {}

    for machine in machines:
        name = machine["name"]

        if name in names:
            raise RuntimeError(f"Duplicate machine name: {name}")
        names[name] = True

        network = machine.get("network", {})

        ip = network.get("provisioning_ip")
        if ip:
            if ip in ips:
                raise RuntimeError(
                    f"Duplicate IP {ip}: {ips[ip]} and {name}"
                )
            ips[ip] = name

        mac = network.get("provisioning_mac")
        if mac:
            mac = mac.lower()

            if mac in macs:
                raise RuntimeError(
                    f"Duplicate MAC {mac}: {macs[mac]} and {name}"
                )
            macs[mac] = name


def show(machines):
    print(f"{'NAME':<16} {'FAMILY':<12} {'GEN':<5} {'IP':<16} {'ROLE'}")

    for machine in machines:
        network = machine.get("network", {})

        print(
            f"{machine['name']:<16} "
            f"{machine.get('family', '-'):<12} "
            f"{machine.get('generation', '-')!s:<5} "
            f"{network.get('provisioning_ip', '-'):<16} "
            f"{machine.get('role', '-')}"
        )


def main():
    machines = load_machines()
    validate(machines)

    if len(sys.argv) == 1 or sys.argv[1] == "list":
        show(machines)
        return

    if sys.argv[1] == "validate":
        print(f"Inventory validation: PASS ({len(machines)} machines)")
        return

    print("Usage:")
    print("  machines.py list")
    print("  machines.py validate")
    sys.exit(1)


if __name__ == "__main__":
    main()
