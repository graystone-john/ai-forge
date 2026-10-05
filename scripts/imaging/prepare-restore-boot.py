#!/usr/bin/env python3
from pathlib import Path
import hashlib
import subprocess
import yaml

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--verify", choices=("full", "fast"), default="full")

import uuid
parser.add_argument("--run-id", default=uuid.uuid4().hex)
args = parser.parse_args()
if len(args.run_id) != 32 or any(c not in "0123456789abcdef" for c in args.run_id):
    parser.error("--run-id must contain 32 lowercase hexadecimal characters")


root = Path(__file__).resolve().parents[2]
cfg = yaml.safe_load((root / "config/forge.yaml").read_text())
server = cfg["provisioning"]["server_ip"]
machine = "daedalus-02"
version = "3.3.3-37"

restore = root / "scripts/imaging/restore-daedalus-02"
subprocess.run(["bash", "-n", str(restore)], check=True)

boot = root / "runtime/http/imaging" / f"clonezilla-{version}"
for name in ("vmlinuz", "initrd.img", "filesystem.squashfs"):
    if not (boot / name).is_file():
        raise SystemExit("Missing boot asset: " + name)

destination = root / "runtime/http" / machine
destination.mkdir(parents=True, exist_ok=True)

# Run restore in a subshell so a failure leaves an interactive recovery shell.
wrapper = """#!/bin/bash
set -u
expected="${1:?Missing restore-script checksum}"
actual="$(sha256sum "$0")"
actual="${actual%% *}"
if [ "$actual" != "$expected" ]; then
    echo "Capture script checksum mismatch. Capture refused."
    exec /bin/bash
fi

echo "Starting offline Daedalus-02 restore."
(
"""
wrapper += f"export AI_FORGE_IMAGE_VERIFY={args.verify}\n"
wrapper += f"export AI_FORGE_RESTORE_RUN_ID={args.run_id}\n"
wrapper += restore.read_text()
wrapper += """
)
result=$?
if [ "$result" -ne 0 ]; then
    echo "RESTORE FAILED with exit code $result."
    echo "Remaining in the live environment. No automatic retry."
    exec /bin/bash
fi

sync
echo "RESTORE VERIFIED. Rebooting into the installed OS."
systemctl reboot
"""

script = destination / "clonezilla-restore.sh"
script.write_text(wrapper)
script.chmod(0o644)
subprocess.run(["bash", "-n", str(script)], check=True)
digest = hashlib.sha256(script.read_bytes()).hexdigest()

base = f"http://{server}/pxe/imaging/clonezilla-{version}"
script_url = f"http://{server}/pxe/{machine}/clonezilla-restore.sh"

ipxe = f"""#!ipxe
echo AI Forge: Clonezilla offline restore of daedalus-02
kernel {base}/vmlinuz initrd=initrd.img boot=live username=user union=overlay config components noswap edd=on nomodeset nodmraid locales=en_US.UTF-8 keyboard-layouts=NONE net.ifnames=0 nosplash noprompt ip=eth0:10.10.10.21:255.255.255.0:10.10.10.1:10.10.10.1 fetch={base}/filesystem.squashfs ocs_prerun="wget -O /tmp/ai-forge-restore {script_url}" ocs_live_run="sudo bash /tmp/ai-forge-restore {digest}" ocs_live_batch=yes
initrd --name initrd.img {base}/initrd.img
boot
"""
(destination / "restore.ipxe").write_text(ipxe)
print("Prepared:", destination / "restore.ipxe")
print("Prepared:", script)
print("Restore script SHA256:", digest)
print("Image verification mode:", args.verify)
