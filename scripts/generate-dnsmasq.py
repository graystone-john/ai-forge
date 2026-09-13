#!/usr/bin/env python3

from pathlib import Path
import yaml
from pxe_policy import read_inventory, bindings, render

ROOT = Path(__file__).resolve().parents[1]
MACHINES_DIR = ROOT / "machines"
OUTPUT_DIR = ROOT / "generated" / "dnsmasq"
OUTPUT_FILE = OUTPUT_DIR / "machines.conf"


def load_machines():
    machines = []

    for machine_file in sorted(MACHINES_DIR.glob("*/machine.yaml")):
        with machine_file.open("r", encoding="utf-8") as f:
            machine = yaml.safe_load(f)

        machines.append(machine)

    return machines


def validate(machines):
    names = set()
    ips = {}
    macs = {}

    for machine in machines:
        name = machine["name"]

        if name in names:
            raise RuntimeError(f"Duplicate machine name: {name}")
        names.add(name)

        network = machine.get("network", {})

        ip = network.get("provisioning_ip")
        mac = network.get("provisioning_mac")

        if ip:
            if ip in ips:
                raise RuntimeError(
                    f"Duplicate IP {ip}: {ips[ip]} and {name}"
                )
            ips[ip] = name

        if mac:
            mac = mac.lower()

            if mac in macs:
                raise RuntimeError(
                    f"Duplicate MAC {mac}: {macs[mac]} and {name}"
                )
            macs[mac] = name


def main():
    machines = read_inventory(ROOT)
    content = render(machines, bindings(ROOT))
    count = sum(bool((m.get("network") or {}).get("provisioning_mac") and (m.get("network") or {}).get("provisioning_ip")) for m in machines)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    from pxe_policy import write_generated
    write_generated(OUTPUT_FILE, content)

    print(f"Generated {OUTPUT_FILE}")
    print(f"Reservations: {count}")


if __name__ == "__main__":
    main()
