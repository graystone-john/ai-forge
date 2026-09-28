#!/usr/bin/env python3

from pathlib import Path
import sys
import yaml

from pxe_policy import identity
from disk_resolver import validate_generated, expected_identity

ROOT = Path(__file__).resolve().parents[1]

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <machine>")
    sys.exit(1)

machine_name = sys.argv[1]

machine_file = ROOT / "machines" / machine_name / "machine.yaml"
provision_file = ROOT / "generated" / machine_name / "provision.ipxe"

machine = yaml.safe_load(machine_file.read_text())
identity(machine)

profiles = {}
for profile_name in machine.get("profiles", []):
    profile_file = ROOT / "profiles" / profile_name / "profile.yaml"
    profiles[profile_name] = yaml.safe_load(profile_file.read_text())

os_profiles = [
    (name, profile["os"])
    for name, profile in profiles.items()
    if "os" in profile
]

if len(os_profiles) != 1:
    raise RuntimeError(
        f"Expected exactly one OS profile; found {len(os_profiles)}"
    )

os_profile_name, os_config = os_profiles[0]
distribution = os_config.get("distribution")

provision = provision_file.read_text()
os_disk = machine["hardware"]["os_disk"]

if distribution == "ubuntu":
    userdata_file = ROOT / "generated" / machine_name / "user-data"

    if not userdata_file.is_file():
        raise RuntimeError("Generated Ubuntu user-data is missing")

    userdata = yaml.safe_load(userdata_file.read_text())
    a = userdata["autoinstall"]
    ssh = a.get("ssh", {})

    if ssh.get("install-server") is not True:
        raise RuntimeError("SSH server is not enabled in autoinstall")

    if ssh.get("allow-pw") is not False:
        raise RuntimeError("SSH password authentication must be disabled")

    authorized_keys = ssh.get("authorized-keys", [])

    if not authorized_keys:
        raise RuntimeError("No SSH authorized key configured")

    if not any(
        key.startswith(("ssh-ed25519 ", "ssh-rsa "))
        for key in authorized_keys
    ):
        raise RuntimeError("No valid SSH public key configured")

    late_commands = a.get("late-commands", [])

    if not any(
        "systemctl enable ssh.service" in cmd
        for cmd in late_commands
    ):
        raise RuntimeError(
            "Autoinstall does not explicitly enable ssh.service"
        )

    validate_generated(a, os_disk)

    if "autoinstall" not in provision:
        raise RuntimeError("provision.ipxe does not enable autoinstall")

    if f"/pxe/{machine_name}/" not in provision:
        raise RuntimeError("Incorrect NoCloud configuration URL")

    print("AI Forge validation: PASS")
    print(f"Machine:       {machine['name']}")
    print(f"Architecture:  {machine['architecture']}")
    print(f"Hostname:      {a['identity']['hostname']}")
    print(f"OS:            Ubuntu {os_config['version']}")
    print(f"OS disk model:       {os_disk['model']}")
    print(f"Hardware serial:     {os_disk['serial']}")
    print("Installer disk: resolved by hardware identity before storage changes")
    print("Disk wipe:     ENABLED")
    print("Autoinstall:   ENABLED")

elif distribution == "arch":
    install_file = (
        ROOT / "generated" / machine_name / "arch" / "install.yaml"
    )

    if not install_file.is_file():
        raise RuntimeError(
            f"Arch install specification is missing: {install_file}"
        )

    install = yaml.safe_load(install_file.read_text())

    if install.get("machine", {}).get("name") != machine["name"]:
        raise RuntimeError("Arch install specification has incorrect machine name")

    if install.get("machine", {}).get("architecture") != machine["architecture"]:
        raise RuntimeError("Arch install specification has incorrect architecture")

    generated_disk = install.get("machine", {}).get("os_disk", {})

    # Validate the safety-critical physical identity fields using the same
    # rules used by the runtime disk resolver.
    expected_source = expected_identity(os_disk)
    expected_generated = expected_identity(generated_disk)

    if expected_generated != expected_source:
        raise RuntimeError(
            "Arch install specification disk identity differs from machine inventory"
        )

    if generated_disk.get("udev_serial") != os_disk.get("udev_serial"):
        raise RuntimeError(
            "Arch install specification udev serial differs from machine inventory"
        )

    expected_urls = (
        f"/pxe/{machine_name}/arch/install.yaml",
        f"/pxe/{machine_name}/arch/install-arch",
        f"/pxe/{machine_name}/arch/disk_resolver.py",
    )

    for url in expected_urls:
        if url not in provision:
            raise RuntimeError(
                f"Arch provision.ipxe is missing required payload URL: {url}"
            )

    if "archiso_http_srv=" not in provision:
        raise RuntimeError(
            "Arch provision.ipxe does not configure ArchISO HTTP root"
        )

    if "archisobasedir=arch" not in provision:
        raise RuntimeError(
            "Arch provision.ipxe does not configure archisobasedir"
        )

    print("AI Forge validation: PASS")
    print(f"Machine:       {machine['name']}")
    print(f"Architecture:  {machine['architecture']}")
    print(f"OS:            Arch Linux ({os_config['version']})")
    print(f"Installer:     {os_config['installer_release']}")
    print(f"OS disk model:       {os_disk['model']}")
    print(f"Hardware serial:     {os_disk['serial']}")
    print(f"Udev serial:         {os_disk['udev_serial']}")
    print(f"Namespace ID:        {os_disk.get('namespace_id')}")
    print("Installer disk: resolved by hardware identity before storage changes")
    print("Disk wipe:     ENABLED")
    print("Arch provision: ENABLED")

else:
    raise RuntimeError(
        f"Unsupported OS distribution in profile {os_profile_name}: "
        f"{distribution!r}"
    )
