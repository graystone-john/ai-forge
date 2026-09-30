#!/usr/bin/env python3

from pathlib import Path
import argparse
import base64
import shutil

import yaml
from disk_resolver import early_command, SENTINEL
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "runtime"
HTTP_ROOT = RUNTIME_ROOT / "http"


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("machine")
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Deploy generated files into the live AI Forge runtime tree",
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

    boot_control_path = ROOT / "scripts" / "target" / "ai-forge-boot-control"

    if not boot_control_path.is_file():
        raise RuntimeError(
            f"AI Forge boot-control helper not found: {boot_control_path}"
        )

    boot_control_b64 = base64.b64encode(
        boot_control_path.read_bytes()
    ).decode("ascii")

    profiles = {}
    for profile_name in machine.get("profiles", []):
        profiles[profile_name] = load_yaml(
            ROOT / "profiles" / profile_name / "profile.yaml"
        )

    os_config = machine.get("os")

    if not isinstance(os_config, dict):
        raise RuntimeError(
            f"Machine {machine_name} has no OS configuration"
        )

    distribution = os_config.get("distribution")
    os_version = os_config.get("version")

    if not distribution or not os_version:
        raise RuntimeError(
            f"Machine {machine_name} requires os.distribution and os.version"
        )

    context = {
        "machine_name": machine["name"],
        "provisioning_server": forge["provisioning"]["server_ip"],
        "provisioning_ip": machine["network"]["provisioning_ip"],
        "username": forge["defaults"]["username"],
        "password_hash": secrets["password_hash"],
        "os_disk_serial": SENTINEL,
        "disk_resolution_command": early_command(machine["hardware"]["os_disk"]),
        "ssh_authorized_key": ssh_authorized_key,
        "provisioning_mac": machine["network"]["provisioning_mac"],
        "boot_control_b64": boot_control_b64,
    }

    if distribution == "ubuntu":
        ubuntu_version = os_config["version"]
        image = forge["images"]["ubuntu"][ubuntu_version]

        context.update({
            "ubuntu_version": ubuntu_version,
            "ubuntu_iso": image["iso"],
            "ubuntu_boot_base_url": image["boot_base_url"],
            "ubuntu_iso_url": image["iso_url"],
        })

        provision_template = "ipxe/provision-ubuntu.ipxe"

    elif distribution == "arch":
        installer_release = os_config["version"]
        image = forge["images"]["arch"][installer_release]
        provisioning = image["provisioning"]

        context.update({
            "arch_installer_release": installer_release,
            "arch_provisioning_release": provisioning["release"],
            "arch_provisioning_http_root": provisioning["http_root"],
            "arch_provisioning_base_url": provisioning["boot_base_url"],
        })

        provision_template = "ipxe/provision-arch.ipxe"

    else:
        raise RuntimeError(
            f"Unsupported OS distribution for machine {machine_name}: "
            f"{distribution!r}"
        )

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
        provision_template: "provision.ipxe",
    }

    if distribution == "ubuntu":
        outputs.update({
            "autoinstall/user-data.yaml.j2": "user-data",
            "autoinstall/meta-data.j2": "meta-data",
        })

    generated = {}

    for template_name, output_name in outputs.items():
        template = env.get_template(template_name)
        rendered = template.render(**context)

        output_file = output_dir / output_name
        output_file.write_text(rendered, encoding="utf-8")

        generated[output_name] = output_file
        print(f"Generated {output_file}")

    if distribution == "ubuntu":
        # Cloud-init's NoCloud datasource probes vendor-data even when no
        # vendor-specific configuration is required. If the file is missing,
        # cloud-init retries the HTTP request for roughly 10 seconds.
        # Publishing an intentionally empty file avoids that unnecessary delay.
        vendor_data_file = output_dir / "vendor-data"
        vendor_data_file.write_text("", encoding="utf-8")

        generated["vendor-data"] = vendor_data_file
        print(f"Generated {vendor_data_file}")

    if args.deploy:
        machine_http = HTTP_ROOT / machine_name
        machine_http.mkdir(parents=True, exist_ok=True)

        # Global entry point currently requested by iPXE.
        shutil.copy2(
            generated["boot.ipxe"],
            HTTP_ROOT / "boot.ipxe",
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

        if distribution == "ubuntu":
            # Ubuntu NoCloud Autoinstall data.
            shutil.copy2(
                generated["user-data"],
                machine_http / "user-data",
            )

            shutil.copy2(
                generated["meta-data"],
                machine_http / "meta-data",
            )

            shutil.copy2(
                generated["vendor-data"],
                machine_http / "vendor-data",
            )

        print()
        print("Deployed:")
        print(f"  {HTTP_ROOT / 'boot.ipxe'}")
        print(f"  {machine_http / 'normal.ipxe'}")
        print(f"  {machine_http / 'provision.ipxe'}")

        if distribution == "ubuntu":
            print(f"  {machine_http / 'user-data'}")
            print(f"  {machine_http / 'meta-data'}")
            print(f"  {machine_http / 'vendor-data'}")


if __name__ == "__main__":
    main()
