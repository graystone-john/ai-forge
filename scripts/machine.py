#!/usr/bin/env python3

from pathlib import Path
import yaml
import sys
from pxe_policy import identity

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
        identity(machine)
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



def init_machine(family):
    import re

    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", family):
        raise SystemExit("Family must use lowercase letters, digits and hyphens.")

    pattern = re.compile(re.escape(family) + r"-(\d+)$")
    numbers = []
    for entry in MACHINES_DIR.iterdir():
        match = pattern.fullmatch(entry.name)
        if match:
            numbers.append(int(match.group(1)))

    generation = 1
    used = set(numbers)
    while generation in used:
        generation += 1

    name = f"{family}-{generation:02d}"

    if len(name) > 63:
        raise SystemExit("Generated machine name exceeds 63 characters.")

    template = MACHINES_DIR / "templates" / "machine.yaml.example"
    directory = MACHINES_DIR / name
    draft = directory / "machine.yaml.example"
    content = template.read_text(encoding="utf-8")

    replacements = {
        "name": ("MACHINE_NAME", name),
        "family": ("MACHINE_FAMILY", family),
        "generation": ("MACHINE_GENERATION", str(generation)),
    }

    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise SystemExit("Template must be a YAML mapping.")

    for field, (placeholder, value) in replacements.items():
        if data.get(field) != placeholder:
            raise SystemExit(f"Expected {field}: {placeholder} in template.")

        content, count = re.subn(
            rf"(?m)^{field}:[ \\t]*{placeholder}[ \\t]*$",
            lambda _, field=field, value=value: f"{field}: {value}",
            content,
        )
        if count != 1:
            raise SystemExit(f"Expected exactly one {field} placeholder.")

    result = yaml.safe_load(content)
    if (
        result.get("name") != name
        or result.get("family") != family
        or result.get("generation") != generation
    ):
        raise SystemExit("Generated draft failed validation.")

    try:
        directory.mkdir()
    except FileExistsError:
        raise SystemExit("Machine directory already exists; rerun to select the next number.")

    with draft.open("x", encoding="utf-8") as stream:
        stream.write(content)

    print(f"Created draft: {draft}")
    print(f"Name: {name}; family: {family}; generation: {generation}")
    print("Remaining placeholders are unchanged. This machine is not registered.")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        import argparse
        parser = argparse.ArgumentParser(prog="./forge machine init")
        parser.add_argument("--family", required=True)
        args = parser.parse_args(sys.argv[2:])
        init_machine(args.family)
        return

    machines = load_machines()
    validate(machines)

    if len(sys.argv) == 1 or sys.argv[1] == "list":
        show(machines)
        return

    if sys.argv[1] == "validate":
        print(f"Inventory validation: PASS ({len(machines)} machines)")
        return

    print("Usage:")
    print("  machine.py list")
    print("  machine.py validate")
    print("  machine.py init --family FAMILY")
    sys.exit(1)


if __name__ == "__main__":
    main()
