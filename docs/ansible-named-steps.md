# AI Forge Ansible Named Steps

AI Forge post-install configuration uses independently named Ansible playbooks.

The previous numbered stage model has been retired. Step names are stable responsibilities and do not imply that new functionality must be inserted by renumbering the workflow.

## Intended lifecycle

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
