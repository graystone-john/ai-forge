#!/usr/bin/env python3
"""Build the FORGE USB drive image without flashing the device."""
from pathlib import Path
import shutil
import subprocess
import tempfile

project = Path(__file__).resolve().parent
repo = project.parents[3]
files = [
    repo / "scripts/inspect-hardware",
    project / "forge-drive/RUN.SH",
]

for tool in ("mkfs.fat", "mcopy"):
    if not shutil.which(tool):
        raise SystemExit(f"Missing {tool}: install dosfstools and mtools.")
for path in files:
    if not path.is_file():
        raise SystemExit(f"Missing file: {path}")

output = project / "build"
output.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=output) as temporary:
    image = Path(temporary) / "forge.img"
    with image.open("wb") as handle:
        handle.truncate(0x180000)
    subprocess.run(
        ["mkfs.fat", "-F", "12", "-n", "FORGE", str(image)],
        check=True,
    )
    for path in files:
        subprocess.run(
            ["mcopy", "-i", str(image), str(path), "::/"],
            check=True,
        )
    image.replace(output / "forge.img")

print(f"Created: {output / 'forge.img'}")
print("Flash offset: 0x670000. Flashing this image replaces stored reports.")
