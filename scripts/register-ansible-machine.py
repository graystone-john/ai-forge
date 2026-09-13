#!/usr/bin/env python3
import argparse
import fcntl
import os
from pathlib import Path
import re
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
MACHINES = ROOT / "machines"
ANSIBLE = ROOT / "ansible"
INVENTORY = ANSIBLE / "inventory" / "hosts.yaml"
HOST_VARS = ANSIBLE / "inventory" / "host_vars"


def fail(message):
    raise SystemExit(f"ERROR: {message}")


def atomic_write(path, text, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if mode is None:
        mode = (path.stat().st_mode & 0o777) if path.exists() else 0o644
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def check_placeholders(value):
    if isinstance(value, dict):
        for item in value.values():
            check_placeholders(item)
    elif isinstance(value, list):
        for item in value:
            check_placeholders(item)
    elif isinstance(value, str) and value.startswith((
        "MACHINE_",
        "OS_DISK_",
        "PROVISIONING_",
        "WIFI_",
        "INFERENCE_",
        "RUNTIME_",
    )):
        fail(f"Unfilled placeholder: {value}")


def runtime_profile_path(profile):
    if not profile:
        fail("Missing machine runtime_profile")
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", str(profile)):
        fail("Invalid runtime_profile")

    path = ANSIBLE / "profiles" / "runtimes" / f"{profile}.yaml"
    if not path.is_file():
        fail(f"Runtime profile does not exist: {path}")

    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict) or not (
        data.get("llama_source_build") or data.get("llama_prebuilt")
    ):
        fail("Runtime profile must define llama_source_build or llama_prebuilt")

    return f"{{{{ playbook_dir }}}}/../profiles/runtimes/{profile}.yaml"


def build_outputs(machine_name, machine):
    network = machine.get("network") or {}
    required = {
        "provisioning_ip": network.get("provisioning_ip"),
        "provisioning_mac": network.get("provisioning_mac"),
        "provisioning_interface": network.get("provisioning_interface"),
        "wifi_interface": network.get("wifi_interface"),
    }

    missing = [name for name, value in required.items() if not value]
    if missing:
        fail(f"Missing machine network fields: {', '.join(missing)}")

    ip = str(required["provisioning_ip"])
    mac = str(required["provisioning_mac"]).lower()
    runtime_profile = str(machine.get("runtime_profile") or "")
    runtime_profile_file = runtime_profile_path(runtime_profile)

    host_file = HOST_VARS / f"{machine_name}.yaml"
    host_vars = {}
    if host_file.is_file():
        loaded = yaml.safe_load(host_file.read_text())
        if isinstance(loaded, dict):
            host_vars = loaded

    host_vars.update({
        "ai_forge_machine": machine_name,
        "ansible_host": ip,
        "ansible_user": (machine.get("ansible") or {}).get("user", "ai-forge"),
        "ansible_python_interpreter": "/usr/bin/python3",
        "ansible_ssh_common_args": "-o StrictHostKeyChecking=accept-new",
        "provisioning": {
            "interface": required["provisioning_interface"],
            "ip": ip,
            "subnet": str(network.get("provisioning_subnet", "10.10.10.0/24")),
            "mac": mac,
        },
        "daedalus_network": {
            "wifi_interface": required["wifi_interface"],
        },
        "inference_profile": machine.get("inference_profile"),
        "runtime_profile": runtime_profile,
        "llama_runtime_profile": runtime_profile_file,
        "llama_build_profile": runtime_profile_file,
        "llama_deploy_profile": runtime_profile_file,
    })

    inventory = yaml.safe_load(INVENTORY.read_text())
    all_group = inventory.setdefault("all", {})
    children = all_group.setdefault("children", {})

    for raw_group in (machine.get("family"), machine.get("role")):
        if not raw_group:
            continue
        group_name = str(raw_group).replace("-", "_")
        group = children.setdefault(group_name, {})
        hosts = group.setdefault("hosts", {})
        hosts[machine_name] = {"ansible_host": ip}

    return {
        host_file: yaml.safe_dump(host_vars, sort_keys=False, allow_unicode=True),
        INVENTORY: yaml.safe_dump(inventory, sort_keys=False, allow_unicode=True),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("machine")
    parser.add_argument("--activate", action="store_true")
    args = parser.parse_args()

    machine_name = args.machine
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", machine_name):
        fail("Invalid machine name")

    directory = MACHINES / machine_name
    draft = directory / "machine.yaml.example"
    active = directory / "machine.yaml"

    lock_path = ROOT / ".registration.lock"
    with lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)

        if args.activate:
            if not draft.is_file():
                fail(f"Draft not found: {draft}")
            if active.exists():
                fail("Machine is already active")
            machine_file = draft
        else:
            if not active.is_file():
                fail(f"Machine is not active: {active}")
            machine_file = active

        machine = yaml.safe_load(machine_file.read_text())
        if not isinstance(machine, dict) or machine.get("name") != machine_name:
            fail("Machine identity does not match")
        check_placeholders(machine)

        outputs = build_outputs(machine_name, machine)
        before = {
            path: (path.read_text(), path.stat().st_mode & 0o777) if path.exists() else None
            for path in outputs
        }

        created_active = False
        try:
            if args.activate:
                os.link(draft, active)
                created_active = True
                import subprocess
                subprocess.run(
                    [str(ROOT / "forge"), "machine", "validate"],
                    cwd=ROOT,
                    text=True,
                    check=True,
                )

            for path, text in outputs.items():
                atomic_write(path, text)

            if args.activate:
                draft.unlink()

        except BaseException:
            for path, old in before.items():
                if old is None:
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        pass
                else:
                    atomic_write(path, old[0], old[1])
            if created_active:
                try:
                    active.unlink()
                except FileNotFoundError:
                    pass
            if args.activate:
                print("Activation failed; draft retained.", file=sys.stderr)
            raise

    if args.activate:
        print(f"Activated: {machine_name}")
        print("Repository inventory updated. No deployment or commit performed.")
        import subprocess
        subprocess.run([str(ROOT / "forge"), "machine", "list"], cwd=ROOT, check=True)
    else:
        print(f"Registered: {machine_name}")

    print(f"Machine: {machine_name}")
    print(f"Address: {machine['network']['provisioning_ip']}")
    print(f"Runtime profile: {machine['runtime_profile']}")


if __name__ == "__main__":
    main()
