#!/usr/bin/env python3
from pathlib import Path
import hashlib
import subprocess
import yaml

root = Path(__file__).resolve().parents[2]
cfg = yaml.safe_load((root / "config/forge.yaml").read_text())
server = cfg["provisioning"]["server_ip"]
machine = "daedalus-02"
version = "3.3.3-37"

capture = root / "scripts/imaging/capture-daedalus-02"
subprocess.run(["bash", "-n", str(capture)], check=True)

boot = root / "runtime/http/imaging" / f"clonezilla-{version}"
for name in ("vmlinuz", "initrd.img", "filesystem.squashfs"):
    if not (boot / name).is_file():
        raise SystemExit("Missing boot asset: " + name)

destination = root / "runtime/http" / machine
destination.mkdir(parents=True, exist_ok=True)

# Run capture in a subshell so a failure leaves an interactive recovery shell.
wrapper = """#!/bin/bash
set -u
expected="${1:?Missing capture-script checksum}"
actual="$(sha256sum "$0")"
actual="${actual%% *}"
if [ "$actual" != "$expected" ]; then
    echo "Capture script checksum mismatch. Capture refused."
    exec /bin/bash
fi

echo "Starting offline Daedalus-02 capture."
(
"""
wrapper += capture.read_text()
wrapper += """
)
result=$?
if [ "$result" -ne 0 ]; then
    echo "CAPTURE FAILED with exit code $result."
    echo "Remaining in the live environment. No automatic retry."
    exec /bin/bash
fi

sync
echo "CAPTURE VERIFIED. Rebooting into the installed OS."
systemctl reboot
"""

script = destination / "clonezilla-capture.sh"
script.write_text(wrapper)
script.chmod(0o644)
subprocess.run(["bash", "-n", str(script)], check=True)
digest = hashlib.sha256(script.read_bytes()).hexdigest()

base = f"http://{server}/pxe/imaging/clonezilla-{version}"
script_url = f"http://{server}/pxe/{machine}/clonezilla-capture.sh"

ipxe = f"""#!ipxe
echo AI Forge: Clonezilla offline capture of daedalus-02
kernel {base}/vmlinuz initrd=initrd.img boot=live username=user union=overlay config components noswap edd=on nomodeset nodmraid locales=en_US.UTF-8 keyboard-layouts=NONE net.ifnames=0 nosplash noprompt ip=eth0:10.10.10.21:255.255.255.0:10.10.10.1:10.10.10.1 fetch={base}/filesystem.squashfs ocs_prerun="wget -O /tmp/ai-forge-capture {script_url}" ocs_live_run="sudo bash /tmp/ai-forge-capture {digest}" ocs_live_batch=yes
initrd --name initrd.img {base}/initrd.img
boot
"""
(destination / "capture.ipxe").write_text(ipxe)
print("Prepared:", destination / "capture.ipxe")
print("Prepared:", script)
print("Capture script SHA256:", digest)
