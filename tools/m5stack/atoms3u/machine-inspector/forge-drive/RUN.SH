#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
echo "AI Forge hardware inspection"
echo "Reports will be saved on this FORGE drive."
lsblk -d -o NAME,SIZE,MODEL,TRAN
read -r -p "Whole disk to inspect (example /dev/nvme0n1): " disk
[[ -n "$disk" ]] || exit 0
sudo -v
bash ./inspect-hardware "$disk"
