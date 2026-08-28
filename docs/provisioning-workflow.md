# AI Forge Provisioning Workflow

AI Forge provides a Git-managed workflow for reproducible bare-metal installation and post-install configuration of local AI machines.

The system intentionally separates:

1. machine definition
2. provisioning artifact generation
3. boot and power control
4. destructive operating-system installation
5. post-install Ansible configuration
6. agent configuration and development

This separation keeps individual operations understandable and allows lower-level capabilities to be tested independently.

## Architecture

The current provisioning environment consists of:

```text
                    Git repository
                         |
                         v
                       Athena
                 provisioning controller
                  10.10.10.1/24
                         |
              dedicated Ethernet network
                         |
                         v
                     Daedalus
                    AI compute node
```

Athena provides the provisioning infrastructure.

Daedalus is the initial managed AI coding node.

## Source of truth

Machine definitions and provisioning configuration originate in Git.

Machine definitions are stored under:

```text
machines/
```

Templates, profiles, Ansible configuration, scripts, and documentation are also Git-managed.

Generated provisioning output and runtime state are derived artifacts and are not the authoritative configuration.

## Provisioning network

Athena uses a dedicated Ethernet interface for the provisioning network:

```text
10.10.10.1/24
```

Current provisioning subnet:

```text
10.10.10.0/24
```

Athena provides:

- DHCP
- TFTP
- iPXE
- HTTP
- boot-control service
- generated Ubuntu Autoinstall configuration

Internet connectivity is provided separately through Athena's normal network connection.

## MAC-based machine discovery

AI Forge uses the provisioning NIC MAC address as the initial hardware identity during PXE boot.

The global iPXE flow chains to the AI Forge boot controller using the machine MAC address.

Conceptually:

```text
UEFI PXE
   ↓
dnsmasq
   ↓
iPXE
   ↓
AI Forge boot controller
   ↓
MAC lookup
   ↓
machine definition
   ↓
normal boot or provisioning boot
```

This allows the controller to determine the correct machine configuration dynamically.

## Normal and provisioning states

A registered machine normally receives non-destructive boot behavior.

Provisioning must be explicitly armed.

This prevents an ordinary PXE boot from automatically reinstalling the operating system.

The provisioning workflow combines:

- generated machine configuration
- one-shot provisioning state
- one-time UEFI PXE selection
- controlled reboot

The target should return to normal boot behavior after the provisioning attempt.

## Operator interface

The primary operator interface is the `forge` command.

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

These commands intentionally use clean operator verbs.

## machines

```bash
./forge machines
```

Lists registered AI Forge machines.

This provides the operator with the known machine inventory without requiring direct inspection of individual YAML files.

## status

```bash
./forge status <machine>
```

Checks the current management status of a machine.

The status path determines whether the machine is reachable and whether the AI Forge SSH management interface is ready.

## wait

```bash
./forge wait <machine>
```

Waits for a machine to reach a requested operational state.

This is used internally by higher-level workflows and can also be useful for operator diagnostics.

## wake

```bash
./forge wake <machine>
```

Wakes a powered-down machine using Wake-on-LAN.

If the machine is already SSH-ready, unnecessary wake behavior is avoided.

After sending Wake-on-LAN, AI Forge waits for the management path to become available.

## deploy

```bash
./forge deploy <machine>
```

Generates and validates provisioning artifacts and publishes them into Athena's live provisioning environment.

Typical generated artifacts include:

```text
boot.ipxe
normal.ipxe
provision.ipxe
meta-data
user-data
```

`deploy` is intentionally non-destructive.

It does not:

- reboot the target
- change the target operating system
- automatically initiate provisioning

This makes deployment independently testable.

## boot

```bash
./forge boot <machine> <action>
```

Provides explicit target boot and power operations.

Current actions include:

```text
status
pxe-next
clear-next
reboot
poweroff
```

### pxe-next

Selects the machine's provisioning NIC as the next UEFI boot device.

The selection is one-time and does not permanently change the normal boot order.

### clear-next

Clears the configured one-time UEFI boot selection.

### reboot

Requests a controlled target reboot.

### poweroff

Requests a controlled target shutdown.

## Restricted boot control

Boot operations are implemented through a root-owned target-side helper:

```text
/usr/local/sbin/ai-forge-boot-control
```

The helper validates operations before changing UEFI or power state.

The one-time PXE operation is constrained to the provisioning MAC configured for the machine.

This avoids granting arbitrary firmware manipulation through the normal operator interface.

## provision

```bash
./forge provision <machine>
```

`provision` is the high-level destructive bare-metal rebuild workflow.

It composes the lower-level capabilities rather than maintaining a separate implementation.

Conceptually:

```text
./forge provision
        |
        +--> deploy
        |
        +--> verify/set one-time PXE BootNext
        |
        +--> arm one-shot provisioning
        |
        +--> reboot target
        |
        +--> remove stale SSH host key
        |
        +--> target PXE boots
        |
        +--> Ubuntu Autoinstall
        |
        +--> target returns with SSH management
```

Because this operation reinstalls the target operating system, it should remain explicit and visibly distinct from `deploy`.

## Ubuntu Autoinstall

AI Forge generates machine-specific Ubuntu Autoinstall configuration.

Templates are maintained under:

```text
templates/autoinstall/
```

Generated configuration includes machine identity, networking, storage, SSH access, and AI Forge target-side management components.

The installation process creates the clean operating-system baseline.

Application and AI configuration are intentionally left to Ansible.

## Target management bootstrap

Autoinstall establishes the minimum management capability required for Athena to take control of the freshly installed target.

This includes the AI Forge SSH management path and target-side management components.

Once SSH is ready, post-install configuration can begin.

## Privilege model

The long-term AI Forge privilege model favors narrowly scoped root-owned helpers.

Restricted helpers already exist for operations such as boot control and agent chat.

The current `ai-forge` Ansible management account still has broad passwordless sudo so Ansible can perform system configuration.

This broader Ansible privilege should be treated separately from the restricted operational interfaces.

The intended direction is to reduce privileges where practical without making machine configuration fragile or unnecessarily complex.

## Post-install configuration

Bare-metal provisioning and post-install configuration are intentionally separate.

PXE and Autoinstall create a clean Ubuntu system.

Ansible transforms that baseline into the intended AI node.

AI Forge uses independently named Ansible steps rather than numbered stages.

The intended lifecycle is:

```text
bootstrap-management
        ↓
base-system
        ↓
reboot
        ↓
post-reboot-validation
        ↓
agent-identity
        ↓
agent-credentials
        ↓
inference
        ↓
coding-tools
        ↓
validate-ai-node
        ↓
agent-workspace
```

Each playbook represents a stable responsibility and should remain independently executable and idempotent where practical.

See:

```text
docs/ansible-named-steps.md
```

## Agent identity

Machine agents use identities separate from both the human operator and the AI Forge management account.

For Daedalus:

```text
Linux user: daedalus
Git user:   Daedalus
Git email:  daedalus@graystone.systems
```

The agent identity is created before its credentials and development workspace are installed.

## Agent credentials

Credentials are installed separately from identity creation.

Daedalus currently receives a dedicated GitHub SSH credential from Athena's controller-side secret store.

Secrets are not stored in the Git repository.

The credential step validates that the resulting identity can authenticate successfully.

## Local inference

The inference step installs the selected model and llama.cpp runtime.

Daedalus exposes an OpenAI-compatible API used by local coding tools.

Validation includes confirming that the configured model is visible through the models endpoint.

## Coding tools

Coding tools are installed independently from the inference runtime.

The current Daedalus implementation uses Aider as the initial coding tool.

Aider is installed from an offline wheelhouse into a managed Python virtual environment.

Local virtual environments such as:

```text
.venv/
```

are machine-local generated state and must not be committed to the AI Forge repository.

## Full-stack validation

After inference and coding tools are installed, AI Forge performs full-stack validation.

Current validation includes:

- approved kernel
- NVIDIA GPU availability
- inference service status
- OpenAI-compatible model endpoint
- chat completion
- Aider coding smoke test

This validates that the machine is actually usable as an AI coding node rather than merely checking that packages were installed.

## Agent workspace

The final development checkout is created after the node has passed the primary AI validation.

For Daedalus:

```text
/home/daedalus/graystone/ai-forge
```

The workspace step validates:

- repository existence
- expected Git remote
- machine Git identity
- clean working tree

Keeping workspace creation late in the lifecycle allows the underlying machine and AI stack to be validated independently.

## Agent development

Configured coding nodes expose an interactive agent interface through:

```bash
./forge chat <machine>
```

For example:

```bash
./forge chat daedalus-01
```

The current Daedalus implementation connects through the AI Forge management path and launches the coding interface under the `daedalus` identity.

The current backend is Aider using Daedalus's local OpenAI-compatible inference service.

When the development checkout is on `main`, the interface is intended to operate in analysis/ask mode.

Editing is performed from a non-main development branch.

See:

```text
docs/agent-architecture.md
```

## Provisioning Performance and Offline Behavior

AI Forge minimizes live-installer work while preserving a standard Ubuntu
Autoinstall workflow and reproducible offline provisioning.

AI Forge publishes an intentionally empty NoCloud `vendor-data` file for each
machine. Cloud-init probes this file even when no vendor-specific configuration
is required. When the file was absent, cloud-init repeatedly received HTTP 404
responses for approximately 10 seconds before continuing. Publishing the empty
file eliminates that retry delay.

During the live installer environment, AI Forge configures snapd with:

    snap set system store.access=offline

This is performed by a transient systemd service created by cloud-init
`bootcmd`. The service exists only in the live environment and prevents snapd
from attempting to contact the Snap Store during offline provisioning.
Subiquity remains available because its local snap is not disabled. Testing
reduced live-installer snap seeding from approximately 34 seconds to
approximately 2 seconds.

The installed target also configures Snap Store access offline so that boot does
not wait for an unavailable public Snap Store. This reduced the observed
`snapd.seeded` boot delay from approximately 33 seconds to effectively
negligible time.

APT geo-IP lookup is disabled and Autoinstall is configured to permit its
offline package fallback. These settings avoid unnecessary dependence on
Internet services during provisioning.

### Rejected installer optimizations

Two additional optimizations were tested on daedalus-01 and deliberately
removed after full bare-metal regression testing exposed changes to the
installed operating system.

Selecting the explicit Autoinstall source `ubuntu-server-minimal` reduced the
Curtin installation phase by approximately 23 seconds, but the resulting target
did not contain baseline utilities expected by AI Forge, including `git` and
`rsync`. AI Forge therefore leaves the Ubuntu installation source at
Subiquity's default selection.

Providing an explicit Autoinstall `network:` configuration selected the
provisioning Ethernet interface by MAC and reduced an observed installer
network phase from approximately 21 seconds to approximately 3 seconds.
However, the resulting target omitted packages required by the established
post-install Wi-Fi path, including `wpasupplicant` and `libpcsclite1`. The
network role could generate valid Wi-Fi Netplan configuration, but the target
could not associate because the required supplicant was absent.

Removing the explicit Autoinstall `network:` block restored Ubuntu's normal
target package selection. On a fresh daedalus-01 installation, `git`, `curl`,
`rsync`, `wpasupplicant`, and `libpcsclite1` were present, the provisioning
Ethernet remained functional, and the existing AI Forge network role restored
Wi-Fi and Internet connectivity after configuration and reboot.

These results establish an important provisioning rule: an installer
optimization is not considered successful merely because installation becomes
faster or reaches SSH successfully. Changes to Subiquity source selection,
network configuration, package behavior, or other installer inputs can alter
the contents and capabilities of the installed target.

Provisioning changes must therefore be validated through the complete AI Forge
reconstruction path:

    bare-metal installation
      -> management SSH
      -> expected baseline packages
      -> provisioning Ethernet
      -> approved kernel
      -> NVIDIA
      -> Wi-Fi association and IPv4
      -> default Internet route and DNS
      -> agent identity and credentials
      -> inference
      -> coding tools
      -> workspace
      -> forge chat

Only optimizations that preserve that complete path should become part of the
standard provisioning configuration.

The retained measured installer-side improvements include approximately 10
seconds from publishing empty NoCloud `vendor-data` and approximately 32
seconds from preventing live-installer Snap Store access. Additional installed
system startup time is saved by keeping Snap Store access offline on the
offline-first target. Measurements are optimization baselines rather than
guarantees for every machine or Ubuntu release.

The performance work reinforces AI Forge's offline-first design: provisioning
should use artifacts supplied by Athena and should not depend on successful
access to public package, Snap, or other Internet services.

## Provisioning design principles

AI Forge follows several core principles:

- Git is the configuration source of truth.
- Generated artifacts are disposable.
- Machine identity is explicit.
- PXE discovery is hardware-aware.
- Destructive operations require explicit intent.
- Lower-level capabilities remain independently usable.
- High-level workflows compose lower-level capabilities.
- Bare-metal installation and application configuration remain separate.
- Machine agents have identities distinct from human and management accounts.
- Secrets and machine-local generated state stay outside Git.
- Validation checks usable outcomes, not merely installation success.

The goal is for a machine to be reproducibly recoverable from its hardware identity, Git-managed configuration, and controller-side secret/runtime data.
