"""Persistent Daedalus-02 host identity, sourced from ai-stores secrets."""
import base64
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MACHINE = 'daedalus-02'
UUID = '87793e9a-50dc-4f4e-ad19-b8a6d42d7a3c'
SERIAL = '21052C800059'
TYPES = ('ed25519', 'ecdsa', 'rsa')


def canonical(machine):
    if machine != MACHINE:
        raise RuntimeError('Persistent identity is configured for daedalus-02 only')
    directory = ROOT.parent / 'ai-stores/secrets/ssh/hosts' / machine
    if directory.is_symlink() or directory.stat().st_mode & 0o077:
        raise RuntimeError('Canonical host-key directory must have mode 0700')
    keys, public = {}, {}
    for kind in TYPES:
        name = f'ssh_host_{kind}_key'
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
            raise RuntimeError('Missing or insecure canonical key: ' + name)
        value = subprocess.check_output(
            ['ssh-keygen', '-y', '-P', '', '-f', str(path)], text=True
        ).strip()
        if value.split()[:2] != (directory / (name + '.pub')).read_text().split()[:2]:
            raise RuntimeError('Canonical public/private key mismatch: ' + name)
        keys[name] = path.read_text()
        public[name] = ' '.join(value.split()[:2])
    return keys, public


# This source contains no private keys. Only EXPECTED public keys are embedded.
TARGET = r'''
import json, os, subprocess, sys, tempfile
from pathlib import Path

def out(*args):
    return subprocess.check_output(args, text=True).strip()

if os.geteuid() != 0:
    raise SystemExit('Run host identity installation as root')
device = Path('/dev/disk/by-uuid/87793e9a-50dc-4f4e-ad19-b8a6d42d7a3c').resolve(strict=True)
tree = json.loads(out('lsblk', '--json', '--inverse', '--paths',
                      '--output', 'NAME,TYPE,SERIAL', str(device)))
def flatten(nodes):
    for node in nodes:
        yield node
        yield from flatten(node.get('children', []))
disks = [n for n in flatten(tree['blockdevices']) if n['type'] == 'disk']
if len(disks) != 1 or (disks[0].get('serial') or '').strip() != '21052C800059':
    raise SystemExit('Host-key accelerator disk identity mismatch')

with tempfile.TemporaryDirectory(prefix='forge-hostkeys-', dir='/run') as work:
    subprocess.run(['mount', '-t', 'ext4', '-o', 'ro,noload', str(device), work], check=True)
    try:
        source = Path(work) / 'secrets/ssh/hosts/daedalus-02'
        keys = {}
        for name, public in EXPECTED.items():
            path = source / name
            if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
                raise SystemExit('Missing or insecure staged key: ' + name)
            actual = out('ssh-keygen', '-y', '-P', '', '-f', str(path))
            if actual.split()[:2] != public.split()[:2]:
                raise SystemExit('Staged host identity does not match ai-stores')
            keys[name] = path.read_bytes()
    finally:
        subprocess.run(['umount', work], check=True)

if sys.argv[1] != '--check':
    target = Path(sys.argv[1]).resolve(strict=True)
    if str(target) not in ('/target', '/mnt') or not target.is_mount():
        raise SystemExit('Expected a mounted installer target')
    ssh = target / 'etc/ssh'
    ssh.mkdir(parents=True, exist_ok=True)
    def write(path, content, mode):
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.forge-')
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, mode)
            os.chown(temporary, 0, 0)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    for name, data in keys.items():
        write(ssh / name, data, 0o600)
        write(ssh / (name + '.pub'), (EXPECTED[name] + '\n').encode(), 0o644)
    cloud = target / 'etc/cloud/cloud.cfg.d'
    cloud.mkdir(parents=True, exist_ok=True)
    write(cloud / '99-zz-ai-forge-host-identity.cfg',
          b'ssh_deletekeys: false\nssh_genkeytypes: []\n', 0o644)
print('Canonical SSH host identity verified' + (' and installed' if sys.argv[1] != '--check' else ''))
'''


def installer_source(machine):
    if machine != MACHINE:
        return ''
    _, public = canonical(machine)
    return 'EXPECTED = ' + repr(public) + '\n' + TARGET


def installer_command(machine, target):
    source = installer_source(machine)
    if not source:
        return ''
    encoded = base64.b64encode(source.encode()).decode()
    return (f"printf '%s' '{encoded}' | base64 -d > /run/ai-forge-host-identity.py\n"
            f'python3 /run/ai-forge-host-identity.py {shlex.quote(target)}')


RECEIVER = r'''
import json, os, subprocess, sys, tempfile
from pathlib import Path
os.umask(0o077)
mount = Path('/mnt/ai-stores-accelerator')
source = subprocess.check_output(['findmnt','-n','-o','SOURCE','--mountpoint',str(mount)], text=True).strip()
uuid = subprocess.check_output(['blkid','-s','UUID','-o','value',source], text=True).strip()
if uuid != '87793e9a-50dc-4f4e-ad19-b8a6d42d7a3c':
    raise SystemExit('Wrong accelerator mount')
tree = json.loads(subprocess.check_output(['lsblk','--json','--inverse','--output','TYPE,SERIAL',source], text=True))
def flatten(nodes):
    for n in nodes:
        yield n
        yield from flatten(n.get('children', []))
disks = [n for n in flatten(tree['blockdevices']) if n['type'] == 'disk']
if len(disks) != 1 or (disks[0].get('serial') or '').strip() != '21052C800059':
    raise SystemExit('Wrong accelerator serial')
payload = json.load(sys.stdin)
parent = mount
for segment in ('secrets','ssh','hosts'):
    parent = parent / segment
    if parent.is_symlink():
        raise SystemExit('Symlink in host-key storage path')
    parent.mkdir(mode=0o700, exist_ok=True)
    os.chown(parent,0,0)
    parent.chmod(0o700)
destination = parent / 'daedalus-02'
if destination.is_symlink():
    raise SystemExit('Symlink in host-key storage path')
names = {f'ssh_host_{kind}_key' for kind in ('ed25519','ecdsa','rsa')}
if set(payload) != names:
    raise SystemExit('Unexpected key payload')
if destination.exists():
    for name, data in payload.items():
        p = destination / name
        if p.is_symlink() or p.read_text() != data:
            raise SystemExit('Existing staged identity differs; explicit rotation required')
        os.chown(p,0,0)
        p.chmod(0o600)
    os.chown(destination,0,0)
    destination.chmod(0o700)
else:
    with tempfile.TemporaryDirectory(dir=parent, prefix='.seed-') as temporary:
        stage = Path(temporary) / 'keys'
        stage.mkdir(mode=0o700)
        for name, data in payload.items():
            p = stage / name
            p.write_text(data)
            p.chmod(0o600)
            public = subprocess.check_output(['ssh-keygen','-y','-P','','-f',str(p)], text=True)
            (stage / (name+'.pub')).write_text(public)
        stage.rename(destination)
os.sync()
print('Canonical SSH keys staged on accelerator SSD')
'''


def stage(machine):
    import yaml
    keys, public = canonical(machine)
    cfg = yaml.safe_load((ROOT / 'config/forge.yaml').read_text())
    spec = yaml.safe_load((ROOT / 'machines' / machine / 'machine.yaml').read_text())
    ip = spec['network']['provisioning_ip']
    user = cfg['defaults']['username']
    with tempfile.TemporaryDirectory(prefix='forge-host-identity-') as temporary:
        known = Path(temporary) / 'known_hosts'
        known.write_text(''.join(ip + ' ' + value + '\n' for value in public.values()))
        subprocess.run([
            'ssh', '-T', '-i', str(ROOT / 'secrets/ssh/id_ed25519_ai_forge'),
            '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'UpdateHostKeys=no',
            '-o', 'UserKnownHostsFile=' + str(known),
            '-o', 'GlobalKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=5',
            '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2',
            user + '@' + ip, 'sudo -n python3 -c ' + shlex.quote(RECEIVER)
        ], input=json.dumps(keys), text=True, check=True)


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3 or sys.argv[1] not in ('stage','check'):
        raise SystemExit('Usage: host_identity.py stage|check daedalus-02')
    if sys.argv[1] == 'stage':
        stage(sys.argv[2])
    else:
        canonical(sys.argv[2])
        print('Canonical host keys available in ai-stores')
