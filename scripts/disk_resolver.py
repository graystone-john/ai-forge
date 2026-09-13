#!/usr/bin/env python3
"""Resolve an NVMe identity before Subiquity storage processing. No disk writes."""
import base64
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

SENTINEL = 'AI_FORGE_DISK_NOT_RESOLVED'

def expected_identity(disk):
    result = {}
    for key in ('model', 'serial'):
        value = disk.get(key)
        if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError('Missing or invalid disk ' + key)
        if value.startswith(('OS_DISK_', 'MACHINE_')):
            raise ValueError('Unfilled disk identity')
        result[key] = value.strip()
    if not result['serial'].strip('0'):
        raise ValueError('Empty hardware serial')
    nsid = disk.get('namespace_id')
    if nsid is not None:
        if isinstance(nsid, bool) or not str(nsid).isdigit() or int(nsid) < 1:
            raise ValueError('Invalid namespace ID')
        result['namespace_id'] = int(nsid)
    return result

def select(expected, rows):
    expected = expected_identity(expected)
    matches = [r for r in rows if r['model'].strip() == expected['model']
               and r['serial'].strip() == expected['serial']
               and ('namespace_id' not in expected or r['namespace_id'] == expected['namespace_id'])]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one hardware match; found {len(matches)}')
    chosen = matches[0]
    value = chosen['udev_serial']
    if not value or any(c in value for c in '*?[]\n\r'):
        raise ValueError('Missing or nonliteral installer serial')
    if sum(r['udev_serial'] == value for r in rows) != 1:
        raise ValueError('Installer serial is not unique')
    if chosen['readonly']:
        raise ValueError('Selected disk is read-only')
    return chosen

def resolve_config(document, expected, rows):
    result = copy.deepcopy(document)
    config = result.get('autoinstall', result)
    disks = [d for d in config['storage']['config'] if d.get('type') == 'disk']
    if len(disks) != 1 or disks[0].get('id') != 'disk-os':
        raise ValueError('Expected exactly one disk-os action')
    if disks[0].get('match') != {'serial': SENTINEL}:
        raise ValueError('Unexpected pre-resolution disk selector')
    if any(k in disks[0] for k in ('path', 'serial', 'wwn')):
        raise ValueError('Conflicting disk selectors')
    chosen = select(expected, rows)
    disks[0]['match'] = {'serial': chosen['udev_serial']}
    return result, chosen

def run(argv):
    return subprocess.check_output(argv, text=True)

def scan():
    subprocess.run(['udevadm', 'settle', '--timeout=30'], check=True)
    devices = json.loads(run(['lsblk', '--json', '--nodeps', '--paths', '--output',
                             'NAME,TYPE,MODEL,SERIAL,RO,TRAN']))['blockdevices']
    rows = []
    for device in devices:
        path = device['name']
        if device['type'] != 'disk' or not re.fullmatch(r'/dev/nvme\d+n\d+', path):
            continue
        if device.get('tran') != 'nvme':
            raise ValueError('Unexpected NVMe transport: ' + path)
        props = dict(line.split('=', 1) for line in run(
            ['udevadm', 'info', '--query=property', '--name=' + path]).splitlines() if '=' in line)
        serial = (device.get('serial') or '').strip()
        if props.get('ID_SERIAL_SHORT', '').strip() != serial:
            raise ValueError('Hardware/udev serial disagreement: ' + path)
        base = Path('/sys/class/block') / Path(path).name
        nsids = {int(p.read_text().strip()) for p in (base/'nsid', base/'device/nsid') if p.is_file()}
        if len(nsids) != 1:
            raise ValueError('Missing or conflicting namespace ID: ' + path)
        rows.append(dict(path=path, model=device.get('model') or '', serial=serial,
                         namespace_id=nsids.pop(), udev_serial=props.get('ID_SERIAL', ''),
                         readonly=device['ro']))
    return rows

def atomic(path, data):
    if path.is_symlink():
        raise ValueError('Refusing symlink: ' + str(path))
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.disk-resolution-')
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def early_command(disk):
    payload = base64.b64encode(json.dumps(expected_identity(disk), sort_keys=True).encode()).decode()
    source = base64.b64encode(Path(__file__).read_bytes()).decode()
    return ("set -eu\numask 077\nprintf '%s' '" + source + "' | base64 -d > /run/ai-forge-disk-resolver.py\n"
            "/usr/bin/python3 /run/ai-forge-disk-resolver.py '" + payload + "'\n")

def validate_generated(config, disk):
    if config.get('early-commands') != [early_command(disk)]:
        raise ValueError('Generated disk resolver or expected identity differs from source')
    disks = [d for d in config['storage']['config'] if d.get('type') == 'disk']
    if len(disks) != 1 or disks[0].get('id') != 'disk-os' or disks[0].get('match') != {'serial': SENTINEL}:
        raise ValueError('Missing unresolved disk guard')
    if any(k in disks[0] for k in ('path', 'serial', 'wwn')):
        raise ValueError('Conflicting generated disk selectors')

def main():
    import yaml
    expected = json.loads(base64.b64decode(sys.argv[1], validate=True))
    path = Path('/autoinstall.yaml')
    document = yaml.safe_load(path.read_text())
    result, chosen = resolve_config(document, expected, scan())
    rendered = yaml.safe_dump(result, sort_keys=False)
    if yaml.safe_load(rendered) != result:
        raise ValueError('Autoinstall round-trip failed')
    audit = {'expected': expected, 'resolved': chosen, 'result': 'unique hardware match'}
    # Never copy the complete autoinstall file into logs: it contains credentials.
    log = Path('/var/log/installer/ai-forge-disk-resolution.json')
    log.parent.mkdir(parents=True, exist_ok=True)
    atomic(log, json.dumps(audit, indent=2)+'\n')
    atomic(path, rendered)
    print('AI Forge disk resolved: ' + json.dumps(audit), flush=True)

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('AI Forge disk resolution FAILED: ' + str(exc), file=sys.stderr)
        sys.exit(1)
