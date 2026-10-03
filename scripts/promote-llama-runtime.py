#!/usr/bin/env python3
"""Promote a verified Arch llama.cpp capture into its source profile."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tarfile
import tempfile
import yaml

def require(condition, message):
    if not condition:
        raise SystemExit(message)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--archive-sha256", required=True)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    store = (root.parent / "ai-stores").resolve()
    profile = args.profile.resolve()
    profile.relative_to((root / "ansible/profiles/runtimes").resolve())
    capture = args.capture_dir.resolve()
    capture.relative_to(store)
    archive = capture / "llama-runtime.tar.gz"

    require(re.fullmatch(r"[0-9a-f]{64}", args.archive_sha256),
            "Invalid archive checksum")
    with archive.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    require(actual == args.archive_sha256, "Archive checksum mismatch")

    original = profile.read_text()
    config = yaml.safe_load(original)
    build = config["llama_source_build"]
    require(build["platform"]["distribution"] == "Archlinux",
            "This promotion helper currently supports Arch captures only")
    captured_build = json.loads((capture / "build-profile.json").read_text())
    for key in ("commit", "configuration_id", "root",
                "cuda_architectures", "cpu_native", "platform"):
        require(build[key] == captured_build[key],
                "Captured build differs from profile: " + key)

    with tarfile.open(archive, "r:gz") as tar:
        names = [member.name for member in tar.getmembers()]
        require(len(names) == len(set(names)), "Duplicate archive members")

        def read(name):
            member = tar.getmember("metadata/" + name)
            require(member.isfile(), "Invalid metadata: " + name)
            return tar.extractfile(member).read()

        provenance = json.loads(read("provenance.json"))
        require(provenance["source_commit"] == build["commit"],
                "Source commit mismatch")
        require(provenance["configuration_id"] == build["configuration_id"],
                "Configuration mismatch")
        require(provenance["original_install_prefix"] == build["root"] + "/runtime",
                "Installation prefix mismatch")
        require(provenance["package_evidence"]["manager"] == "pacman",
                "Capture is not from Arch")
        os_release = read("os-release.txt").decode()
        require(re.search(r'^ID=["\']?arch["\']?$', os_release, re.M),
                "Captured OS is not Arch")

        cmake = read("CMakeCache.txt").decode()
        architecture = re.findall(
            r"^CMAKE_CUDA_ARCHITECTURES:[^=]+=(.+)$", cmake, re.M)
        require(architecture == [str(build["cuda_architectures"])],
                "Captured CUDA architecture mismatch")
        if "120" in str(build["cuda_architectures"]).split(";"):
            require(b"sm_120" in read("cuda-code.txt"),
                    "Missing native sm120 code evidence")

        manifest = json.loads(read("runtime-files.json"))
        actual_paths = {
            m.name[len("runtime/"):]
            for m in tar.getmembers()
            if m.name.startswith("runtime/") and not m.isdir()
        }
        require(actual_paths == set(manifest), "Runtime inventory mismatch")
        for relative, record in manifest.items():
            require(not Path(relative).is_absolute()
                    and ".." not in Path(relative).parts,
                    "Invalid runtime path")
            member = tar.getmember("runtime/" + relative)
            if record["type"] == "symlink":
                require(member.issym() and member.linkname == record["target"],
                        "Runtime symlink mismatch: " + relative)
            else:
                require(record["type"] == "file" and member.isfile(),
                        "Invalid runtime member: " + relative)
                require(member.size == record["size"]
                        and member.mode & 0o7777 == int(record["mode"], 8),
                        "Runtime attributes mismatch: " + relative)
                digest = hashlib.file_digest(
                    tar.extractfile(member), "sha256").hexdigest()
                require(digest == record["sha256"],
                        "Runtime checksum mismatch: " + relative)

        evidence = json.loads(read("arch-runtime-packages.json"))
        packages = evidence["packages"]
        require(isinstance(packages, dict) and packages
                and "nvidia-utils" in packages,
                "Missing runtime package requirements")
        installed = dict(
            line.split(maxsplit=1)
            for line in read("installed-packages.tsv").decode().splitlines()
            if line.strip()
        )
        for name, version in packages.items():
            require(installed.get(name) == version,
                    "Package evidence mismatch: " + name)

        cpu = re.findall(r"^Model name:\s*(.+)$",
                         read("cpu.txt").decode(), re.M)
        gpu = list(__import__("csv").reader(
            io.StringIO(read("gpu.txt").decode())))
        require(len(cpu) == 1 and len(gpu) == 1 and len(gpu[0]) == 3,
                "Expected one captured CPU model and NVIDIA GPU")
        gpu_name, capability, driver = [v.strip() for v in gpu[0]]
        require(capability.replace(".", "") in
                str(build["cuda_architectures"]).split(";"),
                "Captured GPU does not match CUDA build target")

    config["llama_prebuilt"] = {
        "version": build["version"],
        "commit": build["commit"],
        "configuration_id": build["configuration_id"],
        "root": build["root"],
        "archive": "{{ playbook_dir }}/../../../ai-stores/" +
                   archive.relative_to(store).as_posix(),
        "archive_sha256": actual,
        **build["platform"],
        "cpu_model": cpu[0].strip(),
        "gpu_name": gpu_name,
        "compute_capability": capability,
        "driver_version": driver,
        "runtime_packages": packages,
    }
    rendered = yaml.safe_dump(config, sort_keys=False)
    require(profile.read_text() == original,
            "Profile changed during promotion; refusing to overwrite")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=profile.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(rendered)
        temporary.chmod(profile.stat().st_mode & 0o777)
        os.replace(temporary, profile)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print("Promoted Arch runtime:", profile)
    print("Archive SHA256:", actual)
    print("Inference and clean buildless deployment validation remain pending.")

if __name__ == "__main__":
    main()
