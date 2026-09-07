# Daedalus prebuilt runtime regression — 2026-09-07

## Artifact

- llama.cpp: b10612
- Commit: 7584430716ee229751771ed0d6bbcb780d105eeb
- Configuration: ubuntu-noble-amd64-cuda12-sm86-daedalus-native
- Capture: 20260907T024648Z-awpl1yky
- Archive SHA256: 2d4c97b86051b8522d4c51d35b495cf06f4f5bdb048200501aa72004af444fc4
- AI Stores path:
  vault/graystone/llama.cpp/b10612/ubuntu-noble-amd64-cuda12-sm86-daedalus-native/20260907T024648Z-awpl1yky/

## Regression performed

Daedalus was destructively reprovisioned, then configured through the normal
Ansible stages using the captured runtime instead of compiling llama.cpp.

Recorded target:
- Intel Core i9-11900K
- NVIDIA RTX 3090, 24 GB, compute capability 8.6
- Ubuntu Noble amd64
- Kernel 6.8.0-100-generic
- NVIDIA driver 595.84

Passed:
- Prebuilt runtime installation and file verification.
- Verification that inference uses the deployed prebuilt executable.
- Muse text completion and Aider connectivity.
- Direct Muse image requests for Frost, soccer ball, and AEGIS.
- Subsequent routine Frost-only image validation.
- All three image tests through installed Hermes.

Vision tests check successful responses and expected phrases. They do not
certify detailed diagram accuracy or distinguish memorized poem text from OCR.

## Results on Athena

Under ~/graystone/ai-stores/vault/graystone/muse-glimmer-30b/vision/v1/results/:

- direct/b10612/daedalus-01/20260907T044331902450491Z.json
- direct/b10612/daedalus-01/20260907T045455520925001Z.json
- hermes/daedalus-01/20260907T051305052848927Z.json

Routine Frost API test: approximately 19 seconds.
Three Hermes image tests: approximately 3 minutes 55 seconds.

## Test data

Image fixtures remain outside this repository:
- ~/graystone/test-data/vision/v1/
- ~/graystone/test-data/hermes-vision/v1/

Versioned checksums and the routine vision prompts are under tests/.
Hermes prompts and expected phrases are in validate-hermes-agent.yaml.
Back up the actual image fixtures separately; Git does not contain them.

## Follow-up

- Preserve and reboot-test Athena's nginx provisioning-address startup fix.
- Automatically generate artifact documentation during future captures.
- Review obsolete build helpers before deleting them.
