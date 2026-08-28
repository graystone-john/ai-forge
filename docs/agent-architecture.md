# AI Forge Agent Architecture

AI Forge treats machine agents as identities distinct from the human operator and from the Ansible management account.

## Identities

On Daedalus the relevant identities are:

### Human/admin

The human operator administers Athena and Daedalus separately from the machine agent identity.

### AI Forge management account

`ai-forge` is used for controller-driven management and Ansible automation.

It currently has broad passwordless sudo for Ansible. Restricted helpers such as boot control and agent chat have their own explicit sudo rules in preparation for future privilege reduction.

### Daedalus

Daedalus is the coding identity:

```text
Linux user: daedalus
Git identity: Daedalus <daedalus@graystone.systems>
