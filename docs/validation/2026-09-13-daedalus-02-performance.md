# Daedalus-02 performance validation — 2026-09-13

Target: daedalus-02, 10.10.10.21, MAC d8:5e:d3:0e:b8:3c.
Wall meter: shared Shelly at 192.168.0.103, supplied per command.

All seven completed sessions passed with zero GPU collection errors
and zero Shelly errors. Earlier attempts against unreachable daedalus-01
stopped before any workload ran.

## Workload results

| Test | Duration seconds | Prompt tokens/s | Generation tokens/s |
| --- | --- | --- | --- |
| 8192 input, 512 output | 3.620 | 3177.695 | 637.384 |
| 8192 repeated, request 1 | 3.387 | 3170.587 | 638.318 |
| 8192 repeated, request 2 | 3.371 | 3187.309 | 640.461 |
| 32768 input, 512 output | 11.296 | 3141.532 | 594.483 |
| 65536 input, 512 output | 22.795 | 2991.941 | 581.993 |
| 122880 input, 512 output | 45.779 | 2737.550 | 587.431 |
| Sustained request 1 | 45.836 | 2734.117 | 587.525 |
| Sustained request 2 | 45.921 | 2729.605 | 580.257 |
| Sustained request 3 | 45.942 | 2728.165 | 582.391 |
| Sustained request 4 | 45.944 | 2727.559 | 587.460 |
| Sustained request 5 | 45.950 | 2727.221 | 587.700 |

All sustained requests used 122880 input and 512 output tokens.
Prompt throughput declined approximately 0.25% from first to last.
Cached prompt tokens were zero. High speculative draft acceptance makes
these generation rates unsuitable as general coding-speed estimates.

## Power and capacity

Single 120K active window:
- Wall power: sample mean 614.493 W; observed maximum 682.7 W.
- GPU power: sample mean 499.668 W; observed maximum 545.130 W.
- CPU package maximum: 56 C; GPU maximum: 66 C.
- Aggregate CPU mean: 4.248%; busiest logical CPU mean: 97.471%.
- RAM used maximum: 7559.750 MiB; available minimum: 24301.469 MiB.
- Memory PSI some avg10: zero; CPU throttle deltas: zero.

Five-request full capture:
- 277 host samples; 279 valid Shelly readings; zero collection errors.
- Wall sample mean 549.815 W including baseline, gaps, and recovery.
- Observed wall maximum 681.0 W.
- CPU package maximum 62 C; GPU maximum 68 C.
- RAM used maximum 7891.117 MiB.
- VRAM used 23252 MiB of 32607 MiB.
- Swap occupied 1.750 MiB throughout; swap-in/out deltas both zero.
- Memory PSI some avg10 zero; no recorded CPU throttle increase.

## Hermes coding test

Workload: create a CSV power-report CLI and unittest suite.
Started 2026-09-13T02:05:24.141200+00:00.
Ended 2026-09-13T02:06:05.130535+00:00.
Duration 40.989 seconds; Hermes and independent test exits both zero.
Six generated tests passed on rerun; final agent response completed.
Passing generated tests is not independent correctness certification.

82 host samples; 84 valid Shelly readings; zero collection errors.
Whole-capture wall sample mean 287.498 W; observed maximum 644.1 W.
Progress output reached 10.00 GiB RAM; exact peak remains to be derived.
Generated workspace: /tmp/hermes-performance-u1lya7ad on Daedalus-02.
Archive location: generated-project.tar.gz in the workload evidence directory,
with a SHA-256 sidecar; verify preservation before destructive provisioning.

## Evidence

All paths below are relative to:
~/graystone/ai-stores/vault/graystone/performance/v1/

Session directory prefix: sessions/daedalus-02/
- 20260913T013640Z-paired-cc32bb4f
- 20260913T014128Z-paired-17369515
- 20260913T014412Z-paired-ec00ee36
- 20260913T014623Z-paired-9e616968
- 20260913T014820Z-paired-16b6df1f
- 20260913T015209Z-paired-20f4fc58
- 20260913T020511Z-paired-e4d5fe4b

Each session.json links its capture and workload directories.
Hermes workload:
workloads/daedalus-02/20260913T020523Z-hermes-c45dda66/

## Limits and next steps

Means are arithmetic sample means. Wall maxima are observed readings,
not guaranteed transient peaks. Sensor delay and clock alignment are
uncorrected. Telemetry interrupted status reflects deliberate coordinator
shutdown after recovery; these sessions completed successfully.

No dedicated loaded-idle baseline was run on Daedalus-02.
Active-window sustained/Hermes statistics remain to be derived.
GPU throttling flags were not collected.
These tests do not establish long-context answer quality, minimum physical
RAM, or combined maximum CPU/GPU power.

Both performance-hermes and performance-test were extended to allow
daedalus-02 alongside daedalus-01 after verifying the existing daedalus
account, executable, configuration presence, and noninteractive sudo access.

Destructive reprovisioning is planned next. Preserve this baseline and
repeat validation afterward. Raw evidence resides on Athena, outside Git.

## Disposable coding exercise cleanup

The operator confirmed removal of the generated coding exercise at
/tmp/hermes-performance-u1lya7ad on Daedalus-02. These disposable
files are not required for reprovisioning. Earlier workspace/archive
notes describe the pre-cleanup state; archival was not required.
Performance measurements and workload logs remain on Athena.
