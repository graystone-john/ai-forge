# Forge Inspector Report: Command Dispatch Mapping

Table mapping the `forge` operator commands (lines 22–81 of `/home/nispoe/graystone/ai-forge/forge`) to the scripts they dispatch to.

| Forge Command | Dispatch Script | Forge Line |
|---|---|---|
| `machine` / `machines` | `scripts/machine.py` | 24 |
| `status` | `scripts/check-machine` | 32 |
| `wait` | `scripts/wait-machine` | 40 |
| `wake` | `scripts/wake-machine` | 48 |
| `deploy` | `scripts/deploy-machine` | 56 |
| `boot` | `scripts/boot-machine` | 64 |
| `chat` | `scripts/chat-machine` | 72 |
| `provision` | `scripts/provision-machine` | 80 |

*Source: `/home/nispoe/graystone/ai-forge/forge`, lines 22–97. The `case` statement at line 22 routes each command to its respective script under `$ROOT/scripts/`. Unknown commands fall through to the `*` handler at line 83.*
