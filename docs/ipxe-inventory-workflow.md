# Inventory-driven native iPXE

This extension replaces the temporary single-MAC DHCP exception with machine
inventory policy. It does not modify the captured snapshot or original offline
builds. New per-machine builds remain hardware-unvalidated until booted.

## Install on Athena

Extract the updated archive. From its `integration` directory:

```bash
/usr/bin/python3 install-integration.py \
  --forge-root /home/nispoe/graystone/ai-forge \
  --machine daedalus-02 --mac d8:5e:d3:0e:b8:3c --pci-id 1d6a:14c0
```

This prints a review of repository edits. Add `--apply` to install. The installer
requires the source anchors supplied in this session and refuses existing new
integration files. Backups are saved under ai-stores/vault/tools/ipxe/integration-backups.
It updates daedalus-02's parsed machine YAML with the confirmed PCI ID and loader
policy. Other values remain equal, although YAML formatting/comments may change.
It does not deploy live configuration, restart services, arm installation or commit.
Do not run first-install between integration installation and selecting its build:
generation will deliberately stop when a native build has not been selected.

## Prepare daedalus-02 once

```bash
cd ~/graystone/ai-forge
./forge machine validate
./scripts/pxe-machine request daedalus-02 \
  --output ../ai-stores/vault/tools/ipxe/daedalus-02-request-v1.json

sudo unshare --net -- runuser -u nispoe -- /usr/bin/python3 \
  /home/nispoe/graystone/ai-forge/scripts/pxe-machine build \
  --request /home/nispoe/graystone/ai-stores/vault/tools/ipxe/daedalus-02-request-v1.json \
  --snapshot /home/nispoe/graystone/ai-stores/vault/tools/ipxe/native/ff6e520-arm64-v1 \
  --output /home/nispoe/graystone/ai-stores/vault/tools/ipxe/builds/daedalus-02-native-v1 \
  --jobs 4

./scripts/pxe-machine select daedalus-02 \
  --build ../ai-stores/vault/tools/ipxe/builds/daedalus-02-native-v1
```

The build uses the original canonical source and pinned dependency checks, patch,
and configuration. It generates a new Forge embed from the requested MAC and
controller IP, searches net0 through net31 for that MAC, and directly requests
`/forge/boot-mac` using the matching interface. It does not rely on entry.ipxe's
net0 assumption. This new embed needs live testing. No source/package download
is performed; request creation outside the build uses existing Python YAML.
The build itself uses stdlib and the captured ipxe-artifacts helpers, not PyYAML.

Build selection writes relative ai-stores paths and exact hashes to
`config/pxe-loaders.json`. Keep this file and `config/pxe-legacy.json` in Git with
machine metadata. ai-stores must retain the referenced build directories.

## Normal first-install flow

Once a matching Forge build has been selected:

```bash
cd ~/graystone/ai-forge
./forge provision daedalus-02 --first-install
# Manually boot daedalus-02 through its onboard UEFI IPv4 PXE port.
./forge wait daedalus-02 --for ssh --timeout 1200 --interval 5
```

Provisioning wipes the machine's configured OS disk. For a boot-only test first,
keep mode normal and run `scripts/generate-dnsmasq.py` then
`scripts/deploy-dnsmasq`. A successful NORMAL handoff is not proof of a completed
installation; check both separately. Retest daedalus-01's DHCP/HTTP/NORMAL boot
and full deployment before calling the regression complete.

## New hardware

Copy the updated standalone `scripts/inspect-hardware` to the tools USB using
your existing tools preparation workflow. Collect a fresh report and import it
with your existing importer flags. The selected port's PCI vendor/device fields
produce `network.provisioning_pci_id` and `network.provisioning_loader`.
Only 1d6a:14c0 maps to aqc1xx. Other PCI devices map to legacy. Old reports without
PCI IDs are rejected for new imports; recollect them. Non-PCI NIC imports are
not supported by this extension. Existing registered machines without new
fields retain legacy routing. Do not infer PCI identity from a MAC prefix.

For each new native machine, perform request/build/select once after activation.
Then the ordinary first-install command generates and deploys the correct route.
This does not automatically build during installation: missing artifacts stop
before arming. A changed MAC, PCI ID, controller address or edited build requires
a matching new build/selection. Hardware testing remains required for each new
controller and for changes to source/recipe.

## Deployment and rollback

The new deploy-dnsmasq wrapper verifies legacy package pins, all selected native
build inventories and checksums, machine identities, embedded script contents,
and current generated reservations before changing live configuration. It
publishes unique native filenames plus the pinned legacy ipxe.efi, then installs
configuration and syntax-tests/restarts dnsmasq. Backups and transaction records
are saved in ai-stores. A failed live change attempts restoration and restart;
a failed recovery is reported, not treated as success.

```bash
sudo ./scripts/pxe-machine rollback --transaction /absolute/path/printed-by-deployment
```

Rollback refuses changes made since deployment. It restores live files only;
repository configuration still represents the new desired state. Reconcile it
before redeploying. Run while other machines are not provisioning, because
restarting dnsmasq interrupts active DHCP/TFTP operations.

The old `ipxe-loader` tool remains available solely for historical transactions;
its status/deploy guards intentionally reject the new inventory-based routing.
Use the new workflow after migration. Do not mix old rollback operations with new
deployments. To undo the repository integration, use restore-integration.py with
the printed backup; it refuses files edited since installation. Restore any
live integration deployment first. Repository restoration does not undo new Git
commits or change historical artifacts.

## Validation boundary

Included tests exercise policy selection, stale/missing bindings, NIC report
identity, generated routes, installer transformations, and deployment rollback
using fixtures. They do not emulate firmware or prove offline builds work on a
fresh Athena. Athena must run the new build and the physical targets must run the
PXE/provisioning regression. The old diagnostic build's success is not evidence
that this newly generated embed has passed.

After deployment, check static routing, service and loader integrity with:

```bash
sudo ./scripts/pxe-machine status
```

Record each physical result against the full loader checksum printed by status:

```bash
sudo ./scripts/pxe-machine record-test daedalus-02 \
  --test full-provisioning --result pass \
  --expected-sha256 FULL_CHECKSUM_FROM_STATUS \
  --evidence /absolute/path/to/saved-install-log.txt \
  --notes 'Describe observed installation and SSH readiness'
```

Only use pass after observing that result. Repeat applicable tests for daedalus-01.
The evidence record explicitly distinguishes operator observations from static
checksum verification; it does not claim independently witnessed hardware tests.
