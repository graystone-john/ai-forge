# Graystone AI Forge Provisioning Workflow

This document describes the normal machine-control and bare-metal provisioning
workflow used by AI Forge.

## Operator Interface

The preferred operator interface is the top-level `forge` command.

Examples:

    ./forge machines
    ./forge status daedalus-01
    ./forge wake daedalus-01
    ./forge deploy daedalus-01
    ./forge boot daedalus-01 status
    ./forge provision daedalus-01

The primary commands are:

    machines
        List machines known to AI Forge.

    status <machine>
        Check network and AI Forge SSH readiness.

    wake <machine>
        Wake a machine and wait for management readiness.

    deploy <machine>
        Generate, validate, and publish provisioning artifacts without
        rebooting or provisioning the target.

    boot <machine> <action>
        Perform restricted remote firmware/power-control operations.

    provision <machine>
        Perform the complete destructive bare-metal reprovision workflow.

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

## Remote Boot Control

AI Forge exposes restricted remote boot control through:

    ./forge boot <machine> <action>

Supported actions are:

    status
    pxe-next
    clear-next
    reboot
    poweroff

For example:

    ./forge boot daedalus-01 status

The controller does not receive unrestricted passwordless sudo access on the
managed node.

Instead, Autoinstall installs the root-owned helper:

    /usr/local/sbin/ai-forge-boot-control

and machine identity:

    /etc/ai-forge/machine.json

The sudo policy permits the AI Forge management user to execute only specific
boot-control operations through this helper.

The helper discovers the PXE UEFI entry by matching the provisioning MAC
registered for the machine against the MAC embedded in the firmware boot
entry.

It does not accept arbitrary UEFI boot-entry numbers from the remote caller.

The `pxe-next` operation:

1. Reads the registered provisioning MAC.
2. Finds exactly one matching UEFI boot entry.
3. Sets BootNext to that entry.
4. Reads BootNext again and verifies the change.

The `clear-next` operation will clear BootNext only when the current BootNext
is the registered AI Forge PXE entry. It refuses to remove an unrelated
BootNext setting.

Reboot and poweroff are performed through the same restricted helper.

This provides the controller with the privileges required for provisioning
without granting unrestricted passwordless root access.

## Deployment

Generate, validate, and publish a machine's provisioning configuration with:

    ./forge deploy daedalus-01

Deployment performs:

1. Generate machine-specific iPXE and Autoinstall configuration.
2. Validate the machine configuration.
3. Publish the generated artifacts to the provisioning HTTP tree.

Deployment does not modify target firmware, reboot the target, or arm
provisioning.

This separation allows provisioning configuration to be prepared and inspected
independently from destructive machine operations.

Conceptually:

    deploy
        prepare provisioning artifacts

    boot
        control machine boot and power state

    provision
        orchestrate destructive bare-metal reprovisioning

## Remote Provisioning

Provision a running, SSH-ready machine with:

    ./forge provision daedalus-01

The provisioning action performs:

1. Verify the machine is SSH-ready.
2. Run the normal deployment workflow to generate, validate, and publish the
   provisioning configuration.
3. Display the destructive provisioning plan.
4. Ask the target-side boot-control helper to set and verify one-time PXE
   BootNext.
5. Arm AI Forge's one-shot `provision` state.
6. Ask the target-side boot-control helper to reboot the machine.
7. Remove the previous SSH host-key entry after the reboot request because the
   known destructive reprovision will generate a new server identity.

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

AI Forge verifies that BootNext was successfully set before provisioning
continues.

If provisioning fails or is interrupted before the reboot request is
successfully issued, AI Forge attempts to clear the one-time PXE BootNext.

AI Forge will clear BootNext only when it points to the machine's registered
PXE entry.

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

The registered provisioning MAC is also installed on the managed node and is
used by the restricted boot-control helper to identify the correct PXE UEFI
entry.

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

The management username is defined by AI Forge configuration rather than being
hardcoded into the remote boot-control workflow.

## Privileged Operations

AI Forge does not grant its management account unrestricted passwordless sudo.

Operations required for remote provisioning are exposed through the root-owned:

    /usr/local/sbin/ai-forge-boot-control

The sudo policy permits only:

    status
    pxe-next
    clear-next
    reboot
    poweroff

The remote caller cannot supply arbitrary commands, arbitrary UEFI boot-entry
numbers, or arbitrary efibootmgr arguments through this interface.

The helper validates machine identity and provisioning MAC information from:

    /etc/ai-forge/machine.json

This creates a narrow privilege boundary between the controller and the managed
node.

## SSH Host-Key Rotation

A destructive reprovision generates new SSH host keys on the target.

AI Forge removes the previously trusted host-key entry only as part of an
intentional reprovision workflow.

The old host-key entry is removed after the target reboot request has
successfully been issued. It is not removed during configuration generation,
validation, BootNext setup, or provisioning arming.

This preserves the trusted host identity while AI Forge still needs to
communicate with the currently installed operating system.

Global SSH host-key checking must not be disabled.

After a known reprovision, AI Forge permits the newly installed host identity
to be recorded when management SSH first becomes available.

Subsequent SSH connections use normal host-key checking.

Stronger post-install identity verification may be added as part of future
provisioning observability work.

## Failure Safety

The provision workflow fails closed.

Before the destructive reboot, AI Forge tracks two transient conditions:

    BOOTNEXT_SET
    ARMED

Failures and operator interruptions use the same cleanup path.

Examples:

- target not SSH-ready -> stop
- generation fails -> stop
- validation fails -> stop
- no matching PXE entry -> stop
- multiple matching PXE entries -> stop
- BootNext cannot be set or verified -> stop before provisioning is armed
- failure after BootNext is set -> clear AI Forge's PXE BootNext when possible
- failure after provisioning is armed -> reset mode to normal when possible
- Ctrl-C during preparation -> perform the same fail-closed cleanup
- termination during preparation -> perform the same fail-closed cleanup

BootNext cleanup is itself restricted. AI Forge refuses to clear a BootNext
setting belonging to a boot entry other than the machine's registered PXE
entry.

Once the reboot request has successfully been issued, firmware owns the
one-time BootNext transition and AI Forge no longer attempts to clear it.

The one-shot provisioning state is consumed by the controller when the target
requests its provisioning PXE configuration.

## Console Behavior

Autoinstall directs installation and cloud-init output to log files rather than
leaving verbose provisioning output on the normal console.

The installed system should finish booting at a normal login prompt.

Detailed provisioning output remains available through system log files for
diagnostics.

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
2. AI Forge removes the old host-key entry only after the destructive reboot
   request has been successfully issued.
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
