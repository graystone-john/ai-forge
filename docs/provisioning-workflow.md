# Graystone AI Forge Provisioning Workflow

This document describes the normal machine-control and bare-metal provisioning
workflow used by AI Forge.

## Operator Interface

The preferred operator interface is the top-level `forge` command.

Examples:

    ./forge machines
    ./forge status daedalus-01
    ./forge wake daedalus-01
    ./forge provision daedalus-01

The scripts under `scripts/` are implementation components and may also be used
directly for debugging.

## Machine Status

Check whether a machine is ready for AI Forge management:

    ./forge status daedalus-01

The readiness sequence is:

    unreachable
        |
        v
    network reachable
        |
        v
    SSH key authentication succeeds
        |
        v
    READY

SSH readiness, not ping alone, is the authoritative indication that AI Forge
can control the machine.

## Wake-on-LAN

Wake a managed machine with:

    ./forge wake daedalus-01

The wake operation:

1. Checks whether the machine is already SSH-ready.
2. If not, sends a Wake-on-LAN magic packet to the registered provisioning MAC.
3. Waits for the machine to boot.
4. Continues polling until AI Forge SSH authentication succeeds.
5. Reports the machine as ready.

Sending a magic packet alone does not constitute success.

## Normal Boot Architecture

Managed workstation-class systems normally keep their installed OS first in
UEFI boot order.

Example:

    Boot0000* Ubuntu
    Boot0001* UEFI: PXE IPv4 ...

Normal startup therefore follows:

    power on
       |
       v
    SSD / Ubuntu
       |
       v
    network
       |
       v
    sshd
       |
       v
    AI Forge SSH-ready

AI Forge does not require PXE to remain permanently first in firmware.

## Remote Provisioning

Provision a running, SSH-ready machine with:

    ./forge provision daedalus-01

The provisioning action performs:

1. Verify the machine is SSH-ready.
2. Generate machine-specific provisioning configuration.
3. Validate the generated Autoinstall configuration.
4. Deploy PXE and NoCloud artifacts.
5. Read UEFI boot entries remotely.
6. Find exactly one PXE IPv4 entry matching the machine's registered
   provisioning MAC.
7. Display the destructive provisioning plan.
8. Set UEFI `BootNext` to the matching PXE entry.
9. Arm AI Forge's one-shot `provision` state.
10. Remove the previous SSH host-key entry because a known destructive
    reprovision will generate a new server identity.
11. Reboot the machine.

The permanent UEFI `BootOrder` is never modified.

## One-Time PXE

UEFI `BootNext` is used instead of changing permanent firmware boot order.

Example:

    BootOrder: 0000,0001
    Boot0000: Ubuntu
    Boot0001: PXE IPv4

AI Forge temporarily sets:

    BootNext: 0001

The next reboot uses PXE exactly once.

After that boot, firmware automatically returns to the normal BootOrder.

## One-Shot Provisioning State

AI Forge exposes two operator-visible modes:

    normal
    provision

`provision` always means ONE provisioning attempt.

When the target requests its PXE configuration:

    provision
        |
        v
    PXE request received
        |
        v
    controller immediately resets state to normal
        |
        v
    provision.ipxe returned

The machine is disarmed before the destructive installer starts.

This prevents repeated install loops.

## PXE Machine Identification

The common iPXE entry point does not contain a hardcoded machine name.

It sends the provisioning NIC MAC address to the AI Forge controller:

    /forge/boot-mac?mac=<client-mac>

The controller resolves the MAC against:

    machines/*/machine.yaml

Example:

    f0:2f:74:d3:34:d2 -> daedalus-01

Unknown MAC addresses fail closed.

## Storage Safety

The OS disk is selected using the installer-visible udev serial recorded in the
machine inventory.

AI Forge does not rely on device names such as:

    /dev/nvme0n1

because those names may change.

Provision validation fails if the configured storage identity is inconsistent.

## SSH Management

Managed machines receive the AI Forge controller's public management key during
Autoinstall.

Remote SSH uses key authentication.

Password SSH authentication is disabled.

The local account password remains available for console/recovery use.

The AI Forge management private key is local secret material and must never be
committed to Git.

## SSH Host-Key Rotation

A destructive reprovision generates new SSH host keys on the target.

AI Forge removes the previously trusted host-key entry only as part of an
intentional reprovision workflow.

Global SSH host-key checking must not be disabled.

Automatic verification of the newly installed host identity will be addressed
as part of provisioning observability/completion work.

## Failure Safety

The provision workflow fails closed.

Examples:

- target not SSH-ready -> stop
- generation fails -> stop
- validation fails -> stop
- no matching PXE entry -> stop
- multiple matching PXE entries -> stop
- BootNext cannot be set -> stop before provisioning is armed
- failure after provisioning is armed -> reset mode to normal when possible

If BootNext has already been set but provisioning is not armed, the machine may
PXE once but should receive the safe NORMAL response.

## Athena Controller Recovery

The Athena provisioning controller requires:

- provisioning interface with 10.10.10.1
- dnsmasq
- nginx
- AI Forge boot controller

dnsmasq is configured with restart-on-failure protection because its initial
startup may race with creation of the dedicated provisioning interface.

The Athena bootstrap/reproducibility workflow should eventually install and
validate these system configurations automatically.

## Future Work

Separate workstreams handle:

### Privileged Remote Boot Control

Replace interactive sudo used for BootNext/reboot with a least-privilege,
root-owned AI Forge helper.

### Headless Provisioning Observability

Track the full provisioning lifecycle, including:

    armed
    PXE booted
    installer started
    storage
    installing
    installer complete
    rebooting
    SSH ready
    complete
    failed

Provisioning should be considered complete only after the newly installed
system boots and AI Forge management SSH succeeds.

### Host Identity After Reprovisioning

A successful bare-metal reprovision creates new SSH host keys.

AI Forge handles this transition intentionally:

1. The existing host identity must be valid before provisioning begins.
2. AI Forge removes the old host-key entry only after the machine has been
   validated and provisioning has been armed.
3. The newly installed machine is expected to appear at its registered
   provisioning IP.
4. The first AI Forge readiness check after the known reprovision may accept
   and record the new host key.
5. Subsequent SSH connections require that recorded host key normally.

AI Forge must not globally disable SSH host-key checking.

This first-contact trust model is acceptable for the isolated provisioning
network but is not intended to be the final identity-attestation mechanism.
Future provisioning observability may strengthen post-install host identity
verification.

## Managed Node Independence

A normally installed AI Forge node must remain operational when its
provisioning controller is unavailable.

The provisioning Ethernet interface is a management interface, not a boot
dependency.

Managed nodes must therefore satisfy:

- absence of Athena must not significantly delay normal OS boot;
- the provisioning interface must not be marked boot-critical;
- loss of provisioning DHCP must not prevent local login;
- normal Internet connectivity should not depend on the provisioning
  controller when another network path is configured.

During testing, Ubuntu Autoinstall generated the following configuration on
daedalus-01:

    enp5s0:
      critical: true
      dhcp-identifier: "mac"
      dhcp4: true

With athena-01 powered off, systemd-networkd-wait-online waited 120 seconds and
failed before boot continued.

Post-install configuration must replace this behavior so the provisioning
interface is optional/non-blocking.

For daedalus-family systems, Wi-Fi will be configured during post-install
automation and will provide independent Internet/default-route connectivity.
