# AI Forge DEMO

Two AI machines where one builds another, then the built machine
requests its own rebuild through the controller.

The dashboard shows Athena-01, Daedalus-02, and a journal.
Each completed change adds a timestamped journal card.
Git preserves the page and continuation task across OS reinstalls.

## Preview on Athena

    python3 -m http.server 8095 --bind 192.168.0.67 --directory apps/daedalus-demo

Open http://192.168.0.67:8095

## Rebuild checkpoints

Before wiping Daedalus-02, Athena must verify that its work is pushed
and record the exact commit to restore. After provisioning, verify
the restored revision and page, then pause for presentation.

Deployment and automatic continuation are not wired yet.
