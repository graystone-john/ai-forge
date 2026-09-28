#!/usr/bin/env python3

from pathlib import Path
import argparse
import base64
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path):
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("machine")
    args = parser.parse_args()

    machine = load_yaml(
        ROOT / "machines" / args.machine / "machine.yaml"
    )
    forge = load_yaml(ROOT / "config" / "forge.yaml")
    secrets = load_yaml(ROOT / "secrets" / "local.yaml")

    os_profiles = []

    for profile_name in machine.get("profiles", []):
        profile = load_yaml(
            ROOT / "profiles" / profile_name / "profile.yaml"
        )

        if "os" in profile:
            os_profiles.append((profile_name, profile))

    if len(os_profiles) != 1:
        raise RuntimeError(
            f"Expected exactly one OS profile; found {len(os_profiles)}"
        )

    profile_name, profile = os_profiles[0]
    os_config = profile["os"]

    if os_config.get("distribution") != "arch":
        raise RuntimeError(
            f"{profile_name} is not an Arch profile"
        )

    release = str(os_config["installer_release"])
    artifact = forge["images"]["arch"][release]

    public_key_path = (
        ROOT / secrets["ssh"]["management_public_key"]
    )

    if not public_key_path.is_file():
        raise RuntimeError(
            f"Management public key missing: {public_key_path}"
        )

    boot_control_path = (
        ROOT / "scripts" / "target" / "ai-forge-boot-control"
    )

    if not boot_control_path.is_file():
        raise RuntimeError(
            f"Boot control helper missing: {boot_control_path}"
        )

    spec = {
        "machine": {
            "name": machine["name"],
            "architecture": machine["architecture"],
            "os_disk": machine["hardware"]["os_disk"],
            "provisioning_mac":
                machine["network"]["provisioning_mac"],
            "provisioning_ip":
                machine["network"]["provisioning_ip"],
            "provisioning_subnet":
                machine["network"]["provisioning_subnet"],
            "provisioning_interface":
                machine["network"]["provisioning_interface"],
        },
        "provisioning": {
            "server_ip": forge["provisioning"]["server_ip"],
        },
        "os": os_config,
        "bootstrap": artifact,
        "ssh": {
            "user": forge["defaults"]["username"],
            "authorized_key":
                public_key_path.read_text(encoding="utf-8").strip(),
        },
        "boot_control_b64": base64.b64encode(
            boot_control_path.read_bytes()
        ).decode("ascii"),
    }

    out = (
        ROOT
        / "generated"
        / args.machine
        / "arch"
        / "install.yaml"
    )

    out.parent.mkdir(parents=True, exist_ok=True)

    out.write_text(
        yaml.safe_dump(spec, sort_keys=False),
        encoding="utf-8",
    )

    print(f"Generated {out}")


if __name__ == "__main__":
    main()
