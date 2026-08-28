# AI Forge Machine Inventory

AI Forge maintains machine identity and provisioning configuration in Git.

Each managed machine has a machine definition under:

```text
machines/<machine>/
```

The machine definition is the source of truth for hardware identity, provisioning network information, assigned profiles, and other machine-specific configuration.

## Naming model

Machine names use a family name followed by an instance number.

Examples:

```text
athena-01
daedalus-01
```

This allows additional machines in the same family to be added later:

```text
athena-02
daedalus-02
```

The family identifies the general machine class or purpose while the instance number identifies the individual machine.

## Current machines

### athena-01

Athena is the AI Forge provisioning controller.

Current responsibilities include:

- Git repository management
- machine inventory
- provisioning artifact generation
- PXE/iPXE services
- DHCP/TFTP
- HTTP provisioning services
- Ansible controller
- machine lifecycle operations
- controller-side secret storage

Athena uses Wi-Fi for normal network and Internet connectivity and a dedicated Ethernet interface for the AI Forge provisioning network.

Provisioning interface:

```text
10.10.10.1/24
```

Provisioning network:

```text
10.10.10.0/24
```

### daedalus-01

Daedalus is the initial local AI coding node.

Current hardware definition includes:

```text
CPU:         Intel Core i9-11900K
Memory:      64 GB
GPU:         NVIDIA RTX 3090 24 GB
OS disk:     Samsung 980 PRO 2 TB
Architecture: amd64
```

Provisioning identity:

```text
IP:  10.10.10.20
MAC: f0:2f:74:d3:34:d2
```

Daedalus currently provides:

- local GPU inference
- OpenAI-compatible inference API
- Aider coding environment
- dedicated machine-agent identity
- dedicated Git identity and GitHub credential
- development workspace

## Machine definitions

Machine configuration is stored beneath:

```text
machines/
```

A machine definition contains information such as:

- machine name
- family
- generation
- role
- architecture
- hardware
- operating-system disk
- provisioning MAC address
- provisioning IP address
- assigned profiles

Generated provisioning files are derived from these definitions.

Generated output is not the source of truth and should not be manually maintained.

## Machine discovery

The provisioning system uses MAC-address-based discovery.

The global iPXE environment directs a booting machine to the AI Forge boot controller, which resolves the MAC address against registered machine definitions.

Conceptually:

```text
machine PXE boot
      ↓
iPXE
      ↓
boot controller
      ↓
lookup provisioning MAC
      ↓
machine definition
      ↓
normal or provisioning boot behavior
```

This allows machine-specific provisioning behavior without maintaining separate manually configured PXE infrastructure for every target.

## Operator commands

Current machine-oriented operator commands include:

```bash
./forge machines
./forge status <machine>
./forge wait <machine>
./forge wake <machine>
./forge deploy <machine>
./forge boot <machine> <action>
./forge provision <machine>
./forge chat <machine>
```

### machines

Lists registered machines.

### status

Checks whether a machine is reachable and whether the AI Forge SSH management path is ready.

### wait

Waits for a requested machine state such as SSH readiness or offline state.

### wake

Sends Wake-on-LAN when necessary and waits for management readiness.

### deploy

Generates, validates, and publishes provisioning configuration for a machine.

`deploy` does not reboot or reinstall the target.

### boot

Performs explicit boot and power operations through the restricted target-side boot-control interface.

Supported operations currently include:

```text
status
pxe-next
clear-next
reboot
poweroff
```

### provision

Performs the destructive bare-metal provisioning workflow.

This composes lower-level capabilities rather than duplicating them.

### chat

Connects the operator to the configured machine-agent interface.

For Daedalus, the current backend is Aider using the local inference service.

## Planned machine registration

Automated machine registration is part of the intended AI Forge design but is not currently exposed by the `forge` CLI.

The planned interface is:

```bash
./forge register <family> --mac <mac-address>
```

The intended registration workflow will:

1. identify the requested machine family
2. allocate the next available instance number
3. allocate provisioning network configuration
4. create the machine definition
5. validate MAC, IP, and identity conflicts
6. regenerate the appropriate provisioning configuration

For example:

```bash
./forge register daedalus --mac aa:bb:cc:dd:ee:ff
```

could eventually create:

```text
daedalus-02
```

Until registration is implemented, machines are registered through the existing Git-managed machine-definition workflow.

## Planned machine removal

Automated machine removal is also planned but is not currently exposed by the `forge` CLI.

The intended interface is:

```bash
./forge remove <machine>
```

Removal should remove the machine from active provisioning inventory while preserving appropriate historical information through Git.

Machine removal must not silently destroy historical configuration or unrelated runtime data.

## Inventory validation

Machine inventory should be validated before generated configuration is deployed.

Validation should detect conditions such as:

- duplicate machine names
- duplicate provisioning MAC addresses
- duplicate provisioning IP addresses
- invalid addresses
- missing required fields
- invalid profiles
- incompatible architecture or hardware configuration

The goal is to reject inconsistent inventory before it can affect the provisioning environment.

## Source-of-truth policy

Git-managed machine definitions are authoritative.

The following belong in Git:

- machine definitions
- provisioning profiles
- templates
- Ansible roles and playbooks
- scripts
- documentation

The following do not belong in Git:

- secrets
- private keys
- local Python virtual environments
- generated provisioning output
- model files
- installation media
- runtime state
- temporary files

Local virtual environments such as:

```text
.venv/
```

must remain untracked because they contain machine-specific generated files and may contain architecture-specific binaries.
