# Graystone AI Forge Machine Inventory

This document defines the naming, identity, addressing, and lifecycle conventions
for machines managed by Graystone AI Forge.

## Machine Naming

Every physical machine has a unique name consisting of:

    <family>-<instance>

Examples:

    athena-01
    athena-02
    daedalus-01
    daedalus-02

The family name describes the logical machine family or purpose.

Examples:

- `athena` - provisioning/controller nodes
- `daedalus` - local AI/coding nodes

The numeric instance suffix identifies a specific physical machine within that
family.

Instance numbers are zero-padded to two digits.

The numeric suffix is NOT hardcoded into AI Forge logic.

AI Forge should allocate the next available instance number automatically during
machine registration.

For example, if the inventory contains:

    daedalus-01
    daedalus-02

then:

    ./forge register daedalus ...

should create:

    daedalus-03

The machine directory and machine `name` field must use the allocated unique
name:

    machines/daedalus-03/machine.yaml

with:

    name: daedalus-03
    family: daedalus

## Machine Definitions

Active machines are stored under:

    machines/<machine-name>/machine.yaml

Example:

    machines/daedalus-01/machine.yaml

A machine definition should contain:

    name: daedalus-01
    family: daedalus
    generation: 1

The directory name and the `name` field must match.

## Generation

`generation` represents a meaningful hardware or family design revision.

It is NOT a configuration version.

For example, two machines built from the same design may be:

    athena-01   generation: 1
    athena-02   generation: 1

A substantially redesigned Athena platform could later use:

    generation: 2

Normal configuration changes are versioned through Git rather than by changing
the machine generation.

## Provisioning Network

Provisioning subnet:

    10.10.10.0/24

Address allocation:

    10.10.10.1-9       Infrastructure and controller nodes
    10.10.10.10-19     Temporary / unregistered DHCP clients
    10.10.10.20-99     Registered AI Forge machines
    10.10.10.100-254   Reserved for future use

Current controller:

    athena-01   10.10.10.1

Registered machine addresses are stored in each machine's `machine.yaml`.

Example:

    network:
      provisioning_mac: "f0:2f:74:d3:34:d2"
      provisioning_ip: 10.10.10.20
      provisioning_subnet: 10.10.10.0/24

Machine definitions are the source of truth for registered IP assignments.

Do not manually maintain registered `dhcp-host` entries in dnsmasq.

AI Forge generates DHCP reservations from the machine inventory.

## DHCP

Temporary or unknown machines receive addresses from:

    10.10.10.10-19

Registered machines receive persistent DHCP reservations based on:

- machine name
- provisioning MAC address
- provisioning IP address

Generated reservations are written to:

    generated/dnsmasq/machines.conf

Generated files must not be manually edited.

## Machine Registration

The intended machine-registration workflow is:

    ./forge register <family> --mac <mac-address>

Registration should automatically:

1. Scan the active machine inventory.
2. Determine the next available instance number for the requested family.
3. Create the unique machine name `<family>-NN`.
4. Determine the next available registered provisioning IP.
5. Create `machines/<family>-NN/machine.yaml`.
6. Record the provisioning MAC and allocated IP.
7. Validate duplicate names, IP addresses, and MAC addresses.
8. Generate DHCP reservations.
9. Deploy or stage the updated provisioning configuration.

Example:

    ./forge register daedalus --mac aa:bb:cc:dd:ee:ff

If `daedalus-01` already exists, AI Forge may create:

    daedalus-02

and assign:

    10.10.10.21

Neither the instance suffix nor the IP should normally need to be selected
manually.

## PXE Machine Discovery

The common PXE entry point must not contain a hardcoded machine name.

iPXE sends the provisioning NIC MAC address to the AI Forge boot controller.

Example:

    /forge/boot-mac?mac=f0:2f:74:d3:34:d2

The controller searches:

    machines/*/machine.yaml

and resolves the MAC address to the registered unique machine name.

Example:

    f0:2f:74:d3:34:d2 -> daedalus-01

The controller then evaluates that machine's runtime provisioning state and
returns either the normal or provision boot configuration.

This allows the same PXE entry point to support any number of registered
machines without hardcoded `athena-01`, `daedalus-01`, etc. references.

## Machine Removal

Machines should be retired rather than immediately destroyed.

The intended interface is:

    ./forge remove daedalus-02

Removal should:

1. Remove the machine from active provisioning.
2. Remove its DHCP reservation.
3. Remove its live PXE/runtime state.
4. Release its provisioning IP for reuse.
5. Preserve the machine definition in Git history.

Retired machine definitions may also be moved to:

    machines-retired/

Permanent deletion, if needed, should be a separate explicit operation.

## Provisioning Modes

Machines have two user-visible provisioning states:

    normal
    provision

`normal` is always the safe/default state.

`provision` means exactly ONE provisioning attempt.

When a machine in `provision` mode requests its PXE boot configuration, the
AI Forge controller must:

1. Atomically reset the machine state to `normal`.
2. Return the provisioning iPXE configuration.
3. Allow the automated installation to proceed.

This prevents repeated installation loops when PXE remains first in the
machine's firmware boot order.

There is intentionally no persistent destructive provisioning mode.

## Secrets

Secrets must never be committed to Git.

Local secrets are stored under:

    secrets/

For example:

    secrets/local.yaml

The `secrets/` directory must remain excluded by `.gitignore`.

Generated PXE/Autoinstall artifacts should not contain reusable plaintext
secrets when this can reasonably be avoided.

The planned Athena bootstrap process will support importing secrets from
removable USB media into the local secrets store.

## Source of Truth

The general rule is:

    Git-managed machine/profile/config definitions
                    |
                    v
               generators
                    |
                    v
          generated configuration
                    |
                    v
            deployed runtime state

Do not manually edit generated or deployed configuration when the corresponding
setting can be represented in the Git-managed source configuration.

## Provisioning Workflow

The operational boot, Wake-on-LAN, one-time PXE, SSH, and reprovisioning
workflow is documented in:

    docs/provisioning-workflow.md
