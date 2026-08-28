# Graystone AI Forge

Graystone AI Forge is a Git-managed bare-metal provisioning and configuration system for local AI compute nodes.

The system separates machine lifecycle management, post-install configuration, and agent development into distinct layers.

## Architecture

The current environment consists of:

- **Athena** — provisioning/controller node.
- **Daedalus** — local AI coding node.
- Git-managed machine definitions under `machines/`.
- PXE/iPXE and Ubuntu Autoinstall for bare-metal installation.
- Ansible for post-install configuration.
- Local inference using llama.cpp and an OpenAI-compatible API.
- Aider as the initial coding tool.
- Per-machine agent identities, credentials, and development workspaces.

## Operator interface

The primary bare-metal interface is:

```bash
./forge machines
./forge status <machine>
./forge wait <machine>
./forge wake <machine>
./forge deploy <machine>
./forge boot <machine> <action>
./forge provision <machine>
./forge chat <machine>
