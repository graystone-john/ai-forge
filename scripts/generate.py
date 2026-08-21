#!/usr/bin/env python3

from pathlib import Path
import sys
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <machine>")
        sys.exit(1)

    machine_name = sys.argv[1]

    forge = load_yaml(ROOT / "config" / "forge.yaml")
    machine = load_yaml(ROOT / "machines" / machine_name / "machine.yaml")

    profiles = {}
    for profile_name in machine.get("profiles", []):
        profiles[profile_name] = load_yaml(
            ROOT / "profiles" / profile_name / "profile.yaml"
        )

    ubuntu = profiles["ubuntu-ai-node"]["os"]
    ubuntu_version = ubuntu["version"]

    context = {
        "machine_name": machine["name"],
        "provisioning_server": forge["provisioning"]["server_ip"],
        "ubuntu_version": ubuntu_version,
        "ubuntu_iso": forge["images"]["ubuntu"][ubuntu_version]["iso"],
    }

    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )

    template = env.get_template("ipxe/ubuntu-server.ipxe")
    rendered = template.render(**context)

    output_dir = ROOT / "generated" / machine_name
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "boot.ipxe"
    output_file.write_text(rendered, encoding="utf-8")

    print(f"Generated {output_file}")


if __name__ == "__main__":
    main()
