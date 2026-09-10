# Daedalus Shelly power measurements — 2026-09-09

## Measurement setup

- Target: daedalus-01.
- Meter: Shelly Plug US Gen4, connected to Daedalus's power supply.
- Local address for these runs: 192.168.0.103.
- Athena records read-only Switch.GetStatus responses.
- The plug is shared equipment, selected with --shelly on the command line.
- No permanent machine assignment; no outlet switching or counter resets.
- Raw data resides in AI Stores; this report resides in AI Forge.

## What changed from September 8

September 8 established CPU, RAM, GPU and inference baselines, using
manually observed wall readings. Those results remain historical evidence.

September 9 adds timestamped whole-system power and current measurements.
Manual observations are not measured averages or guaranteed maxima.
The September 8 8K observations of 124 W and 191 W should not be treated
as its loaded power range: subsequent automated 8K capture reached 494.5 W.

Synthetic inference throughput is not representative Hermes coding speed.
The repetitive fixture strongly favors speculative draft acceptance.

## Completed captures

- 30-second integration smoke test: 76.846 W sample mean, 94.0 W
  observed maximum; no reported Shelly errors.
- Paired 8K input / 512 output test: 8.198 seconds; 49 valid Shelly
  readings across the full capture; no errors; 494.5 W observed maximum.
- 10-minute loaded idle: 531 valid readings from 532 attempts;
  76.965 W sample mean, 74.8 W minimum, 98.8 W observed maximum.
  One HTTP timeout; maximum valid-reading gap 8.663 seconds.
  Retained as an idle baseline with a documented gap, not a gap-free capture.
- Paired 122880 input / 512 output test: details below.

## Longer inference workload

- Request duration: 117.542 seconds.
- Active Shelly readings: 116.
- Maximum active reading gap: 3.000 seconds.
- Full capture: 159 valid Shelly readings, no reported errors.
- Full-capture sample mean: 381.423 W, including baseline and recovery.
- Host telemetry: 160 samples, no reported GPU errors.
- Telemetry status "interrupted" reflects the coordinator's planned stop.

| Measurement | Minimum | Sample mean | Maximum |
| --- | --- | --- | --- |
| Wall power (W) | 95.200 | 470.743 | 495.700 |
| Current (A) | 0.822 | 4.048 | 4.249 |
| Voltage (V) | 118.600 | 118.980 | 121.400 |

Window boundaries use Athena polling timestamps and Daedalus request
timestamps. Clock offset and sensor delay have not been measured.
The low initial reading includes the transition into load.
All means above are arithmetic sample means, not integrated energy averages.
Zero HTTP errors does not imply perfectly spaced or fresh sensor samples.

## Recorder changes

- Added performance_shelly.py and optional --shelly integration.
- Preserved raw responses, request timestamps, HTTP duration and errors.
- Changed polling from a one-second delay after each response to scheduled
  polling, skipping missed deadlines without catch-up bursts.
- Replaced the manual reset instruction during Shelly captures.
- Any Shelly error currently marks the meter capture degraded and causes
  the enclosing test to report failure; saved evidence remains available.

## Evidence

Paths below are relative to the AI Stores performance/v1 directory:

- Smoke: results/daedalus-01/20260909T223322Z-idle-50bacc34/
- 8K session: sessions/daedalus-01/20260909T223520Z-paired-ed2e0bbe/
- Idle: results/daedalus-01/20260909T223955Z-idle-6ad081e8/
- Longer session: sessions/daedalus-01/20260909T225308Z-paired-c773bb30/
- Longer telemetry: results/daedalus-01/20260909T225309Z-heavy-inference-0dae4223/
- Longer workload: workloads/daedalus-01/20260909T225321Z-inference-122880-158be33d/
- Derived window statistics: sessions/daedalus-01/20260909T225308Z-paired-c773bb30/shelly-workload-summary.json

Raw evidence is excluded from Git and requires separate backup.

## Conclusions and remaining work

Observed loaded wall power averages approximately 471 W during this
synthetic request, with an observed maximum of 495.7 W.
Observed loaded current averages approximately 4.05 A, peaking at 4.249 A.

These results do not establish worst-case machine draw or circuit capacity.
Long-duration sustained inference, simultaneous heavy CPU/GPU load,
and startup transients have not been characterized.
Circuit assessment also requires other loads on the same circuit.

Before comparing hardware configurations, preserve their identities and
runtime settings and repeat the same workload and measurement procedure.

<!-- sustained-20260909-start -->
## Sustained inference — five requests, 23:00 UTC

Five sequential requests, each with 122880 input and 512 output tokens.
Statistics below exclude the gaps between requests and recovery.

| Request | Duration s | Wall mean W | Wall max W | CPU max °C | GPU max °C | RAM max GiB | Invalid polls |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 117.462 | 469.00 | 497.50 | 69.00 | 66.00 | 4.93 | 0 |
| 2 | 118.110 | 473.31 | 498.30 | 70.00 | 67.00 | 4.93 | 0 |
| 3 | 118.166 | 474.78 | 499.10 | 71.00 | 67.00 | 4.95 | 0 |
| 4 | 118.160 | 475.91 | 499.50 | 71.00 | 67.00 | 5.01 | 0 |
| 5 | 118.089 | 475.26 | 498.60 | 71.00 | 67.00 | 4.96 | 2 |

The full capture has 752 host samples and 726 valid Shelly readings
from 729 attempts. Three requests to the meter timed out: two during
workload 5 and one during recovery. Maximum valid-reading gap: 5 seconds.
The recorder was manually stopped after recovery; evidence was preserved.

Across the full capture, recorded CPU thermal-throttle counters stayed
at zero and swap use stayed at zero. GPU throttling flags were not collected.
Prompt throughput remained within approximately 0.6% across the five requests.

Means are sample means. Clock alignment and sensor delay are uncorrected.
This workload primarily exercises prompt processing; it is not a combined
CPU/GPU maximum-power test or a representative Hermes coding benchmark.

Evidence: `/home/nispoe/graystone/ai-stores/vault/graystone/performance/v1/results/daedalus-01/20260909T230021Z-heavy-inference-ca01335f`
Derived statistics: `sustained-workload-summary.json` in that directory.

The repeat coordinator was subsequently verified with two successful
8K requests in session `20260909T231526Z-paired-551205e6`.
Its one Shelly timeout occurred during recovery. Future degraded captures
are labeled completed_with_gaps while retaining a nonzero exit code.
<!-- sustained-20260909-end -->

## Paired Hermes coding workload — 23:28 UTC

- Date: 2026-09-09.
- Workload duration: 80.353 seconds.
- Hermes completed its final response; exit code 0.
- Created power_report.py and test_power_report.py.
- Eight generated tests passed when rerun by the runner; exit code 0.
- Overall session: completed.
- Host telemetry: 122 samples; zero GPU collection errors.
- Shelly: 123 valid readings, zero errors.
- Largest Shelly reading gap: 1.084 seconds.
- Whole-capture wall power: minimum 76.0 W, sample mean 341.564 W,
  observed maximum 497.0 W.

Power statistics include baseline and recovery. Active-workload statistics
remain to be derived. Means are arithmetic sample means; observed maxima
do not establish transient peaks. Sensor delay and clock differences are
uncorrected. Passing generated tests is not independent certification
of program correctness.

Telemetry was deliberately interrupted by the coordinator after recovery;
the workload and Shelly capture completed successfully.

Evidence paths relative to the performance/v1 vault directory:
- sessions/daedalus-01/20260909T232758Z-paired-1d3b2f5a/
- results/daedalus-01/20260909T232759Z-hermes-8bdee3f5/
- workloads/daedalus-01/20260909T232811Z-hermes-66cae2a0/

Generated project remains at /tmp/hermes-performance-ye0i4wow on Daedalus;
archival has not been confirmed.

Operator command:
    scripts/performance-test daedalus-01 --workload hermes --repeat 1 --shelly 192.168.0.103

The Shelly address is supplied per run because the plug moves between
machines. One command coordinates the workload, telemetry, and wall power.
