#!/usr/bin/env python3

from pathlib import Path
import argparse
import shutil

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path.home() / "graystone" / "provisioning-data"


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("machine")
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Deploy generated files into the live provisioning-data tree",
    )
    args = parser.parse_args()

    machine_name = args.machine

    forge = load_yaml(ROOT / "config" / "forge.yaml")
    machine = load_yaml(ROOT / "machines" / machine_name / "machine.yaml")
    secrets = load_yaml(ROOT / "secrets" / "local.yaml")
    ssh_public_key_path = ROOT / secrets["ssh"]["management_public_key"]

    if not ssh_public_key_path.is_file():
        raise RuntimeError(
            f"SSH management public key not found: {ssh_public_key_path}"
        )

    ssh_authorized_key = ssh_public_key_path.read_text(
        encoding="utf-8"
    ).strip()


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
        "username": forge["defaults"]["username"],
        "password_hash": secrets["password_hash"],
        "os_disk_serial": machine["hardware"]["os_disk"]["udev_serial"],
	"ssh_authorized_key": ssh_authorized_key,
    }

    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )

    output_dir = ROOT / "generated" / machine_name
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {
        "ipxe/entry.ipxe": "boot.ipxe",
        "ipxe/normal.ipxe": "normal.ipxe",
        "ipxe/provision.ipxe": "provision.ipxe",
        "autoinstall/user-data.yaml.j2": "user-data",
        "autoinstall/meta-data.j2": "meta-data",
    }

    generated = {}

    for template_name, output_name in outputs.items():
        template = env.get_template(template_name)
        rendered = template.render(**context)

        output_file = output_dir / output_name
        output_file.write_text(rendered, encoding="utf-8")

        generated[output_name] = output_file
        print(f"Generated {output_file}")

    if args.deploy:
        machine_http = DATA_ROOT / "http" / machine_name
        machine_http.mkdir(parents=True, exist_ok=True)

        # Global entry point currently requested by iPXE.
        shutil.copy2(
            generated["boot.ipxe"],
            DATA_ROOT / "http" / "boot.ipxe",
        )

        # Machine-specific boot modes.
        shutil.copy2(
            generated["normal.ipxe"],
            machine_http / "normal.ipxe",
        )

        shutil.copy2(
            generated["provision.ipxe"],
            machine_http / "provision.ipxe",
        )

        # Ubuntu NoCloud Autoinstall data.
        shutil.copy2(
            generated["user-data"],
            machine_http / "user-data",
        )

        shutil.copy2(
            generated["meta-data"],
            machine_http / "meta-data",
        )

        # Never change an existing machine's mode during deployment.
        # New machines always begin in safe NORMAL mode.
        mode_file = machine_http / "mode.ipxe"

        if not mode_file.exists():
            shutil.copy2(
                generated["normal.ipxe"],
                mode_file,
            )

        print()
        print("Deployed:")
        print(f"  {DATA_ROOT / 'http' / 'boot.ipxe'}")
        print(f"  {machine_http / 'normal.ipxe'}")
        print(f"  {machine_http / 'provision.ipxe'}")
        print(f"  {mode_file}")
        print(f"  {machine_http / 'user-data'}")
        print(f"  {machine_http / 'meta-data'}")

if __name__ == "__main__":
    main()
