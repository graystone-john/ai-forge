#!/usr/bin/env python3
"""Prepare an offline runtime dependency repository and pinned deployment profile."""
import argparse
import datetime
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import yaml

REMOTE = r'''
import hashlib, json, os, pathlib, subprocess, sys
spec = json.load(sys.stdin)
runtime = pathlib.Path(spec['root']) / 'runtime'
env = dict(os.environ, LC_ALL='C')
env.pop('LD_LIBRARY_PATH', None)
def run(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, env=env).strip()
external = set()
elfs = []
actual = {p.relative_to(runtime).as_posix() for p in runtime.rglob('*') if p.is_symlink() or not p.is_dir()}
if actual != set(spec['manifest']):
    raise SystemExit('Runtime file inventory changed since capture')
for relative, record in spec['manifest'].items():
    path = runtime / relative
    if not path.resolve().is_relative_to(runtime.resolve()):
        raise SystemExit('Runtime path leaves installation: ' + relative)
    if record['type'] == 'symlink':
        if not path.is_symlink() or os.readlink(path) != record['target']:
            raise SystemExit('Changed symbolic link: ' + relative)
        continue
    with path.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != record['sha256']:
            raise SystemExit('Runtime changed since capture: ' + relative)
    if path.stat().st_mode & 0o7777 != int(record['mode'], 8):
        raise SystemExit('Runtime file permissions changed: ' + relative)
    with path.open('rb') as stream:
        if stream.read(4) != b'\x7fELF':
            continue
    result = subprocess.run(['ldd', str(path)], text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, env=env)
    if result.returncode:
        if 'statically linked' in result.stdout or 'not a dynamic executable' in result.stdout:
            continue
        raise SystemExit(result.stdout)
    if 'not found' in result.stdout:
        raise SystemExit('Unresolved library: ' + result.stdout)
    elfs.append({'file': relative, 'ldd': result.stdout})
    for line in result.stdout.splitlines():
        text = line.split('=>', 1)[-1].strip()
        if text.startswith('/'):
            library = pathlib.Path(text.split()[0]).resolve()
            if not library.is_relative_to(runtime.resolve()):
                external.add(str(library))
owners = {}
for library in sorted(external):
    candidates = [library]
    if library.startswith('/usr/lib/'):
        candidates.append(library[4:])
    if library.startswith('/usr/lib64/'):
        candidates.append(library[4:])
    found = set()
    for candidate in candidates:
        result = subprocess.run(['dpkg-query', '-S', candidate], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                package, separator, owned = line.partition(': ')
                if separator and owned == candidate:
                    found.add(package)
    if len(found) != 1:
        raise SystemExit('Ambiguous or unpackaged library owner: ' + library + ' ' + repr(found))
    package = found.pop()
    version = run(['dpkg-query', '-W', '-f=${Version}', package])
    owners[library] = {'package': package.split(':')[0], 'version': version}
print(json.dumps({'libraries': owners, 'elfs': elfs}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--forge-root', type=Path, required=True)
    parser.add_argument('--machine', required=True)
    parser.add_argument('--profile', required=True,
                        help='Existing unified runtime profile name or path to update')
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z][a-z0-9-]*', args.machine):
        raise ValueError('Invalid machine name')
    root = args.forge_root.expanduser().resolve()
    store = root.parent / 'ai-stores'
    capture = args.capture.expanduser().resolve()
    capture.relative_to(store.resolve())
    acquisition = store / 'modules/linux/ubuntu/noble/llama-cpp-build/b10612/cuda12.8-sm120/scripts/acquire-sm120-dependencies.py'
    loader = importlib.util.spec_from_file_location('acquisition', acquisition)
    apt = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(apt)
    archive = capture / 'llama-runtime.tar.gz'
    if apt.sha(archive) != args.expected_sha256:
        raise ValueError('Runtime archive checksum differs from the confirmed capture')
    build = json.loads((capture / 'build-profile.json').read_text())
    machine = yaml.safe_load((root / f'machines/{args.machine}/machine.yaml').read_text())
    manifest = Path(build['package_manifest']).resolve()
    dependencies = manifest.parent
    dependencies.relative_to(store.resolve())
    dependency_record = json.loads((dependencies / 'capture.json').read_text())
    if dependency_record['validation'].get('local_repository_baseline_solve') != 'passed':
        raise ValueError('Build dependency capture lacks baseline validation')
    for filename in ['amd64-closure.tsv', 'baseline.dpkg-status', 'baseline.holds',
                     'apt/dists/noble/main/binary-amd64/Packages', 'apt/dists/noble/Release']:
        if apt.sha(dependencies / filename) != dependency_record['files'][filename]:
            raise ValueError('Build dependency evidence changed: ' + filename)
    profile_arg = Path(args.profile)
    if profile_arg.suffix == '.yaml' or profile_arg.parent != Path('.'):
        profile_path = profile_arg.expanduser()
        if not profile_path.is_absolute():
            profile_path = root / profile_path
    else:
        if not re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', args.profile):
            raise ValueError('Invalid runtime profile name')
        profile_path = root / f'ansible/profiles/runtimes/{args.profile}.yaml'

    if not profile_path.is_file():
        raise ValueError('Runtime profile does not exist: ' + str(profile_path))

    profile_data = yaml.safe_load(profile_path.read_text())
    if not isinstance(profile_data, dict) or not isinstance(profile_data.get('llama_source_build'), dict):
        raise ValueError('Runtime profile must define llama_source_build before promotion')

    if profile_data['llama_source_build'].get('commit') != build['commit']:
        raise ValueError('Runtime profile source commit differs from capture')
    if profile_data['llama_source_build'].get('configuration_id') != build['configuration_id']:
        raise ValueError('Runtime profile configuration differs from capture')
    runtime_manifest = json.loads((capture / 'evidence/runtime-files.json').read_text())
    with tarfile.open(archive, 'r:gz') as captured:
        for filename in ['runtime-files.json', 'cpu.txt', 'gpu.txt']:
            if captured.extractfile('metadata/' + filename).read() != (capture / 'evidence' / filename).read_bytes():
                raise ValueError('Evidence differs from checked archive: ' + filename)
        provenance = json.load(captured.extractfile('metadata/provenance.json'))
        if provenance['source_commit'] != build['commit'] or provenance['original_install_prefix'] != build['root'] + '/runtime':
            raise ValueError('Build profile differs from archived provenance')
    remote = ['ssh', '-o', 'BatchMode=yes', '-i', str(root / 'secrets/ssh/id_ed25519_ai_forge'),
              (machine.get('ansible') or {}).get('user', 'ai-forge') + '@' + machine['network']['provisioning_ip'],
              shlex.join(['python3', '-c', REMOTE])]
    print('Verifying captured files and library ownership on ' + args.machine, flush=True)
    result = subprocess.run(remote, input=json.dumps({'root': build['root'], 'manifest': runtime_manifest}),
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise ValueError(result.stderr or result.stdout)
    evidence = json.loads(result.stdout)
    roots = {}
    driver = {}
    for library, item in evidence['libraries'].items():
        selected = driver if item['package'].startswith('libnvidia-') else roots
        previous = selected.setdefault(item['package'], item['version'])
        if previous != item['version']:
            raise ValueError('Conflicting installed versions')
    if not roots or not driver:
        raise ValueError('Expected both runtime libraries and NVIDIA driver prerequisites')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = capture / 'runtime-dependencies' / stamp
    out.mkdir(parents=True)
    apt.write_json(out / 'library-owners.json', evidence)
    sources = f'deb [arch=amd64 trusted=yes] {(dependencies / "apt").as_uri()} noble main\n'
    baseline, held = apt.baseline_status((dependencies / 'baseline.dpkg-status').read_text(), (dependencies / 'baseline.holds').read_text())
    environments = {}
    for kind in ['empty', 'baseline']:
        environments[kind] = apt.apt_environment(out / kind, sources)
        if kind == 'baseline':
            (out / kind / 'status').write_text(baseline)
        apt.run(['apt-get', '-o', 'APT::Update::Error-Mode=any', 'update'], env=environments[kind])
    def simulate(kind, pins, turn):
        command = ['apt-get', '--simulate', '--no-remove', '--no-install-recommends', 'install'] + pins
        result = subprocess.run(command, env=environments[kind], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (out / f'solve-{turn}-{kind}.log').write_text(result.stdout)
        if result.returncode:
            raise ValueError(result.stdout)
        return result.stdout
    solution = apt.converge(simulate, [f'{p}={v}' for p, v in roots.items()], held)
    forbidden = [p for p in solution if not p.endswith('-config-common')
                 and not re.fullmatch(r'gcc-\d+-base', p)
                 and re.match(r'^(?:gcc(?:-|$)|g\+\+(?:-|$)|cpp(?:-|$)|cmake|build-essential|cuda-(?:toolkit|nvcc|compiler|tools)|.*-dev(?:-|$))', p)]
    if forbidden:
        raise ValueError('Runtime closure unexpectedly requires build tools: ' + repr(forbidden))
    packages = {(p['package'], p['version']):p for p in dependency_record['packages']}
    repo = out / 'apt'
    pool = repo / 'pool/main'
    pool.mkdir(parents=True)
    for name, version in sorted(solution.items()):
        package = packages[(name, version)]
        source = dependencies / package['file']
        if not source.resolve().is_relative_to(dependencies) or apt.sha(source) != package['sha256']:
            raise ValueError('Dependency package changed: ' + name)
        shutil.copy2(source, pool / source.name)
    manifest_path = out / 'amd64-closure.tsv'
    manifest_path.write_text('# Package\tVersion\n' + ''.join(f'{p}\t{v}\n' for p,v in sorted(solution.items())))
    dist = repo / 'dists/noble/main/binary-amd64'
    dist.mkdir(parents=True)
    scan = subprocess.run(['dpkg-scanpackages', '--multiversion', 'pool/main', '/dev/null'], cwd=repo, text=True, capture_output=True, check=True)
    (dist / 'Packages').write_text(scan.stdout)
    (dist / 'Packages.gz').write_bytes(gzip.compress(scan.stdout.encode(), mtime=0))
    (repo / 'dists/noble/Release').write_text(apt.run(['apt-ftparchive', '-o', 'APT::FTPArchive::Release::Codename=noble', '-o', 'APT::FTPArchive::Release::Suite=noble', '-o', 'APT::FTPArchive::Release::Architectures=amd64', '-o', 'APT::FTPArchive::Release::Components=main', 'release', 'dists/noble'], cwd=repo))
    for kind in ['empty', 'baseline']:
        env = apt.apt_environment(out / ('offline-' + kind), f'deb [trusted=yes arch=amd64] {repo.as_uri()} noble main\n')
        if kind == 'baseline':
            (out / ('offline-' + kind) / 'status').write_text(baseline)
        apt.run(['apt-get', 'update'], env=env)
        plan = apt.run(['apt-get', '--simulate', '--no-remove', '--no-install-recommends', 'install'] + [f'{p}={v}' for p,v in solution.items()], env=env)
        apt.protect_plan(apt.plan_packages(plan), held)
        (out / ('offline-' + kind + '.log')).write_text(plan)
    gpu = (capture / 'evidence/gpu.txt').read_text().strip().splitlines()
    if len(gpu) != 1:
        raise ValueError('Expected a captured single NVIDIA GPU')
    gpu_name, capability, driver_version = [v.strip() for v in gpu[0].split(',')]
    cpu = re.findall(r'^Model name:\s*(.+)$', (capture / 'evidence/cpu.txt').read_text(), re.M)
    if len(cpu) != 1 or cpu[0].strip() != machine['hardware']['cpu']:
        raise ValueError('Captured CPU differs from registered machine')
    relative = out.relative_to(store).as_posix()
    prebuilt = {
        'version': build['version'], 'commit': build['commit'], 'configuration_id': build['configuration_id'],
        'root': build['root'], 'archive': '{{ playbook_dir }}/../../../ai-stores/' + archive.relative_to(store).as_posix(),
        'archive_sha256': args.expected_sha256,
        'package_manifest': '{{ playbook_dir }}/../../../ai-stores/' + relative + '/amd64-closure.tsv',
        'package_manifest_sha256': apt.sha(manifest_path),
        'apt_repository': build['apt_repository'].split('/vault/', 1)[0] + '/' + relative + '/apt',
        **build['platform'], 'cpu_model': cpu[0].strip(), 'gpu_name': gpu_name,
        'compute_capability': capability, 'driver_version': driver_version,
        'driver_packages': [{'package': p, 'version': v} for p,v in sorted(driver.items())],
        'library_paths': sorted({str(Path(p).parent) for p in evidence['libraries'] if p.startswith('/usr/local/cuda-')}),
    }
    apt.write_json(out / 'runtime-dependencies.json', {'roots': roots, 'solution': solution,
        'driver_prerequisites': driver, 'baseline_sha256': dependency_record['baseline_status_sha256'],
        'archive_sha256': args.expected_sha256,
        'validation': 'Offline empty and recorded-baseline dependency simulations passed; full regression pending'})
    profile_data['llama_prebuilt'] = prebuilt
    rendered = yaml.safe_dump(profile_data, sort_keys=False, allow_unicode=True)
    yaml.safe_load(rendered)
    profile_path.write_text(rendered)
    print(f'Runtime packages: {len(solution)} (no compilers/development packages)')
    print('Runtime profile updated: ' + str(profile_path))
    print('Runtime dependencies: ' + str(out))
    print('Full clean provisioning and inference/vision/Hermes regression remains pending.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        sys.exit('ERROR: ' + str(error))
