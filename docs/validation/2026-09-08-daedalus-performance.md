# Daedalus performance and wall-power measurements — 2026-09-08

## Purpose

Measure idle, sustained Hermes, and heavier-inference workloads to understand
system memory use and whole-machine power demand.

Circuit capacity assessment remains pending: circuit rating, other loads on
the same circuit, and loaded-machine measurements are not yet recorded.

## Measurement method

- Controller: Athena.
- Target: daedalus-01, provisioning IP 10.10.10.20.
- Recorder: AI Forge `scripts/performance-machine`.
- Target telemetry collected over management SSH at one-second intervals.
- Whole-machine AC power observed manually using a meter before the PSU.
- GPU telemetry reports GPU power separately from whole-machine wall power.
- Raw telemetry and summaries are preserved in AI Stores.
- Loaded-server state is supported by captured service/PID/VRAM evidence;
  see verified full-run results below.

Reported RAM usage is MemTotal minus MemAvailable. It is a whole-host memory
pressure measure, not total process allocations; reclaimable file cache is
largely counted as available. GPU VRAM is measured separately.

Console progress displays selected samples. Its displayed ranges are not
necessarily the extrema across all recorded samples.

## Idle baseline

- Run ID: `20260908T032253Z-idle-384034ca`
- Capture started: `2026-09-08T03:22:54.007809+00:00`
- Requested duration: 600 seconds.
- Completed samples: 600.
- GPU missing/error samples: 0.
- Workload: no active Hermes requests.
- Initial wall observation before the run: approximately 77 W.

Full-run statistics are recorded in **Verified full-run idle results** below.

The two wall readings are preserved as reported. They are not a measured
average or a confirmed meter-held minimum/maximum. No amperage, power factor,
energy consumption, or meter model has yet been recorded.

### Evidence

Athena run directory:

`~/graystone/ai-stores/vault/graystone/performance/v1/results/daedalus-01/20260908T032253Z-idle-384034ca/`

Files:

- `manifest.json`: recorder identity, repository state, and run parameters.
- `telemetry.jsonl`: target metadata and timestamped samples.
- `summary.json`: statistics across captured samples.
- `ssh.stderr.log`: SSH diagnostics.
- `wall-meter.csv`: manual-reading template; reported readings are documented
  here and have not yet been entered into that CSV.

### Preliminary interpretation

Observed idle wall power was approximately 80 W. Displayed system RAM and GPU
power readings were stable over the observation window.

This establishes an initial idle observation, not a workload peak or a maximum
machine power rating. Captured service/PID/VRAM evidence supports loaded-server idle;
exact model/runtime settings remain unverified.

## Remaining measurements

1. Verify exact model, runtime artifact, context, and DFlash settings before loaded-workload comparisons.
2. Record meter identity, circuit rating, and other equipment on the circuit.
3. Capture a fixed sustained Hermes workload with its prompt and starting state.
4. Capture heavier inference with documented input size and generation settings.
5. Capture recovery idle and repeat workloads to assess variation.

For comparisons, record model/runtime identity, context configuration, GPU power
limit, cache state, workload duration, and background activity.

Software samples and an ordinary wall meter may miss brief power transients.
Observed workload peaks alone do not establish that a shared circuit cannot trip.

## Verified full-run idle results

The capture completed 600 samples in 600.038 seconds, with no GPU
missing/error samples. Statistics below use all recorded samples and
supersede the earlier console-progress ranges.

| Measurement | Sample mean | Observed range |
| --- | --- | --- |
| Whole-machine wall power | Not measured | Operator readings: 78.1–80.6 W |
| GPU power | 24.97 W | 24.28–25.95 W |
| System RAM used | 1.88 GiB | 1.84–2.09 GiB |
| System RAM available | 60.74 GiB | 60.54–60.78 GiB |
| CPU busy | 0.225 % | 0.062–4.446 % |
| GPU VRAM used | 18302.00 MiB | 18302.00–18302.00 MiB |
| GPU utilization | 0.00 % | 0.00–0.00 % |
| GPU temperature | 35.70 °C | 34.00–37.00 °C |
| Swap used | 0.00 MiB | 0.00–0.00 MiB |

### Loaded-server evidence

- Inference service: active, MainPID 1186.
- NVIDIA process snapshot: PID 1186 was `llama-server`, using 18,284 MiB VRAM.
- Total GPU VRAM usage: 18,302 MiB throughout the capture.
- Configured GPU power limit: 390 W.
- NVIDIA driver: 595.84.
- Kernel: 6.8.0-100-generic.
- CPU: Intel Core i9-11900K, 8 cores / 16 logical CPUs.

These observations support a loaded-server idle baseline. The recorder's
inference executable lookup returned null; the reason was not captured.
Exact runtime artifact, model identity, context settings, and DFlash settings
were not verified by this capture.

The configured GPU power limit is not a whole-machine wall-power limit.
Wall readings remain manually reported observations, not a measured average
or a confirmed meter-held maximum.

### Next measurement

Capture a reproducible sustained Hermes workload, preserving its prompt,
starting project state, runtime settings, elapsed time, and output alongside
telemetry and manual wall-meter observations.

## Hermes coding smoke retry — 03:48 UTC

- Workload duration: 145.098 seconds, including initialization and test rerun.
- Full telemetry capture: 360 samples; no GPU missing/error samples.
- Operator-reported wall readings: **413 W and 504 W**.
- Highest reported wall reading so far: **504 W**; not a guaranteed maximum.
- Six agent-generated tests passed on independent rerun.
- Final response failed with a server-side `peg-native` format error
  after the 12-iteration limit was reached.
- Hermes and the workload wrapper returned zero despite that error.
- Classification: useful load measurement; incomplete agent completion.

### Statistics during the workload window

| Measurement | Sample mean | Minimum | Maximum |
| --- | --- | --- | --- |
| CPU busy | 6.398 % | 3.131 % | 7.442 % |
| RAM used | 2.503 GiB | 1.992 GiB | 3.546 GiB |
| RAM available | 60.122 GiB | 59.079 GiB | 60.633 GiB |
| Swap used | 0.000 MiB | 0.000 MiB | 0.000 MiB |
| GPU power | 368.346 W | 25.160 W | 389.680 W |
| GPU utilization | 93.048 % | 0.000 % | 100.000 % |
| GPU VRAM | 18318.428 MiB | 18302.000 MiB | 18320.000 MiB |
| GPU temperature | 62.097 °C | 40.000 °C | 68.000 °C |

Sample timestamps select the workload window; sensor polling and
CPU averaging intervals may overlap its boundaries slightly.

### Evidence

- Capture: `/home/nispoe/graystone/ai-stores/vault/graystone/performance/v1/results/daedalus-01/20260908T034804Z-hermes-f8d1aad0`
- Workload: `/home/nispoe/graystone/ai-stores/vault/graystone/performance/v1/workloads/daedalus-01/20260908T034812Z-hermes-2417e6d9`
- Derived statistics: `active-window-summary.json` in the workload directory.
- Generated project remains on Daedalus at
  `/tmp/hermes-performance-gxbxwryc`; not yet archived.

### Runner findings

The earlier attempt stopped with Hermes process state T. Terminal job
control was suspected. Adding `timeout --foreground` allowed the retry
to perform inference and tool execution.

Before sustained repetitions, strengthen completion checks to detect
agent/server errors even when the process returns zero.

## Hermes CPU/RAM capacity repeat — 04:04 UTC

- Workload duration: 126.876 seconds.
- Wall readings reported by operator: 472 W and 503 W; average unknown.
- Final response completed; eight generated tests passed on rerun.
- The previous peg-native error did not recur in this attempt.
- Full capture: 360 samples, no GPU missing/error samples.

### Active-workload measurements

| Measurement | Sample mean | Minimum | Maximum |
| --- | --- | --- | --- |
| Aggregate CPU busy | 6.415 % | 1.187 % | 6.942 % |
| Busiest logical CPU per sample | 93.535 % | 9.091 % | 100.000 % |
| cpu0_busy_pct | 0.070 % | 0.000 % | 2.970 % |
| cpu10_busy_pct | 12.492 % | 0.000 % | 100.000 % |
| cpu11_busy_pct | 18.074 % | 0.000 % | 100.000 % |
| cpu12_busy_pct | 0.110 % | 0.000 % | 6.000 % |
| cpu13_busy_pct | 0.023 % | 0.000 % | 2.941 % |
| cpu14_busy_pct | 0.133 % | 0.000 % | 6.000 % |
| cpu15_busy_pct | 0.079 % | 0.000 % | 4.000 % |
| cpu1_busy_pct | 0.094 % | 0.000 % | 3.960 % |
| cpu2_busy_pct | 53.080 % | 0.000 % | 100.000 % |
| cpu3_busy_pct | 15.959 % | 0.000 % | 100.000 % |
| cpu4_busy_pct | 1.309 % | 0.000 % | 5.051 % |
| cpu5_busy_pct | 0.818 % | 0.000 % | 4.950 % |
| cpu6_busy_pct | 0.330 % | 0.000 % | 2.970 % |
| cpu7_busy_pct | 0.031 % | 0.000 % | 1.010 % |
| cpu8_busy_pct | 0.000 % | 0.000 % | 0.000 % |
| cpu9_busy_pct | 0.000 % | 0.000 % | 0.000 % |
| cpu_temp_hwmon4_core_0_c | 38.756 °C | 31.000 °C | 43.000 °C |
| cpu_temp_hwmon4_core_1_c | 39.165 °C | 33.000 °C | 46.000 °C |
| cpu_temp_hwmon4_core_2_c | 53.307 °C | 36.000 °C | 67.000 °C |
| cpu_temp_hwmon4_core_3_c | 46.299 °C | 34.000 °C | 65.000 °C |
| cpu_temp_hwmon4_core_4_c | 40.984 °C | 31.000 °C | 45.000 °C |
| cpu_temp_hwmon4_core_5_c | 38.701 °C | 34.000 °C | 44.000 °C |
| cpu_temp_hwmon4_core_6_c | 36.709 °C | 31.000 °C | 39.000 °C |
| cpu_temp_hwmon4_core_7_c | 37.039 °C | 32.000 °C | 42.000 °C |
| cpu_temp_hwmon4_package_id_0_c | 62.079 °C | 40.000 °C | 67.000 °C |
| ram_used_mib | 3.538 GiB | 2.770 GiB | 3.645 GiB |
| ram_available_mib | 59.087 GiB | 58.980 GiB | 59.855 GiB |
| ram_cached_mib | 17.730 GiB | 17.730 GiB | 17.733 GiB |
| ram_anon_mib | 1.858 GiB | 1.139 GiB | 1.951 GiB |
| swap_used_mib | 0.000 GiB | 0.000 GiB | 0.000 GiB |
| psi_cpu_full_avg10_pct | 0.000 % | 0.000 % | 0.000 % |
| psi_cpu_some_avg10_pct | 0.000 % | 0.000 % | 0.000 % |
| psi_io_full_avg10_pct | 0.000 % | 0.000 % | 0.000 % |
| psi_io_some_avg10_pct | 0.000 % | 0.000 % | 0.000 % |
| psi_memory_full_avg10_pct | 0.000 % | 0.000 % | 0.000 % |
| psi_memory_some_avg10_pct | 0.000 % | 0.000 % | 0.000 % |
| GPU power_w | 368.105 W | 25.780 W | 389.660 W |
| GPU utilization_pct | 92.701 % | 0.000 % | 100.000 % |
| GPU vram_used_mib | 18320.000 MiB | 18320.000 MiB | 18320.000 MiB |
| GPU temperature_c | 62.079 °C | 42.000 °C | 66.000 °C |

### Counter changes across the workload

- `oom_kill_since_start`: 0.0
- `pgmajfault_since_start`: 1.0
- `psi_cpu_full_stall_us_since_start`: 0.0
- `psi_cpu_some_stall_us_since_start`: 54896.0
- `psi_io_full_stall_us_since_start`: 51375.0
- `psi_io_some_stall_us_since_start`: 58324.0
- `psi_memory_full_stall_us_since_start`: 0.0
- `psi_memory_some_stall_us_since_start`: 0.0
- `pswpin_since_start`: 0.0
- `pswpout_since_start`: 0.0
- Thermal-throttle counter changes: all recorded counters remained unchanged.

Counter differences use the last pre-workload sample and last sample
inside the workload. Boundaries are approximate. Shared thermal counters
must not be summed. PSI avg10 is a rolling ten-second measurement.
Major faults can reflect file-backed reads rather than swap.

### Evidence

- Capture: `/home/nispoe/graystone/ai-stores/vault/graystone/performance/v1/results/daedalus-01/20260908T040431Z-hermes-96e36e81`
- Workload and derived summary: `/home/nispoe/graystone/ai-stores/vault/graystone/performance/v1/workloads/daedalus-01/20260908T040439Z-hermes-bd2c422e`
- Generated project remains at `/tmp/hermes-performance-dbg5d6wb`
  on Daedalus; not yet archived.

These results cover a short coding workload. They do not establish the
minimum RAM or CPU needed for long contexts or concurrent workloads.

## Configuration change — live context increased to 131072

After the initial Hermes capacity tests, live API inspection confirmed:

- `/health`: ok.
- Active context: 131072 tokens, previously observed as 65536.
- Inference slots: 1.
- Model alias: muse-glimmer-30b.
- Model artifact path unchanged.

The exact change time and whether other settings changed were not recorded.
Earlier captures are retained as historical results; their individual context
settings were not captured. New runs must be identified as the 131072-context
configuration.

Collect a fresh idle baseline before direct inference testing. Configured
context capacity is distinct from the number of tokens used in a request.

## Paired direct inference — 8192 tokens, 04:32 UTC

- Configured context: 131072 tokens; one slot.
- Evaluated input: 8192 tokens; generated output: 512 tokens.
- Request duration: 7.713 seconds.
- Prompt processing: 6.189 seconds, 1323.689 tokens/s.
- Generation: 1.521 seconds, 335.896 tokens/s.
- Cached prompt tokens: 0. Draft acceptance: 479/479.
- Operator wall observations: 124 W and 191 W; average unknown.
- Active-request telemetry samples: 8.
- Full paired capture: 49 samples, no GPU missing/error samples.

| Measurement | Sample mean | Sample maximum |
| --- | --- | --- |
| Aggregate CPU busy | 6.073 % | 6.375 % |
| Busiest logical CPU | 89.929 % | 100.000 % |
| RAM used | 4.234 GiB | 4.398 GiB |
| File cache | 21.255 GiB | 21.255 GiB |
| Swap used | 0.000 GiB | 0.000 GiB |
| CPU package temperature | 55.875 °C | 60.000 °C |
| GPU power | 322.517 W | 391.770 W |
| GPU utilization | 94.000 % | 100.000 % |
| GPU VRAM | 21.205 GiB | 21.205 GiB |
| GPU temperature | 55.750 °C | 58.000 °C |

This synthetic request is short and highly favorable to speculative
draft acceptance. It is not a sustained-power or Hermes-speed benchmark.
One-second samples cannot accurately resolve all generation-phase peaks.

Session evidence: `/home/nispoe/graystone/ai-stores/vault/graystone/performance/v1/sessions/daedalus-01/20260908T043235Z-paired-3f37ca09`

## Paired direct inference — 32768 tokens, 04:35 UTC

- Configured context: 131072 tokens; one slot.
- Input: 32768 tokens; output: 512 tokens; cached prompt tokens: zero.
- Prompt processing: 25.755 seconds, 1272.294 tokens/s.
- Generation: 1.698 seconds, 300.892 tokens/s.
- Total request: 27.462 seconds.
- Active-request telemetry: 27 samples.
- Wall readings: not supplied.

| Measurement | Sample mean | Sample maximum |
| --- | --- | --- |
| Aggregate CPU busy | 6.366% | 6.437% |
| Busiest logical CPU | 99.670% | 100% |
| CPU package temperature | 58.889°C | 62°C |
| RAM used | 4375.552 MiB | 4537.719 MiB |
| File cache | 21765.324 MiB | 21765.328 MiB |
| Swap used | 0 MiB | 0 MiB |
| Memory PSI some avg10 | 0% | 0% |
| GPU power | 360.111 W | 387.970 W |
| GPU utilization | 90.259% | 100% |
| GPU VRAM | 21714 MiB | 21714 MiB |
| GPU temperature | 59.185°C | 62°C |

Minimum available system RAM: 59590.414 MiB.

Evidence:
`~/graystone/ai-stores/vault/graystone/performance/v1/sessions/daedalus-01/20260908T043449Z-paired-0841bddb/`

One logical CPU was almost continuously busy, while most aggregate CPU capacity
remained unused. This does not identify whether the busy thread is performing
computation or actively waiting for GPU work.

The earlier 8K run's manual wall observations of 124 W and 191 W did not
capture the whole-machine draw corresponding to its sampled GPU peak of
391.77 W. They must not be interpreted as that workload's power range.

No minimum CPU/RAM configuration has yet been validated.

## Paired direct inference — 65536 tokens, 04:38 UTC

- Input: 65536 tokens; output: 512; cached prompt tokens: zero.
- Total request: 56.923 seconds.
- Prompt processing: 55.241 seconds, 1186.365 tokens/s.
- Generation: 1.666 seconds, 306.704 tokens/s.
- Draft acceptance: 478/494.
- Reported wall observations: 438 W and 501 W; average unknown.
- Active samples: 57; full capture: 99 samples.

| Measurement | Sample mean | Minimum | Maximum |
| --- | --- | --- | --- |
| Aggregate CPU busy | 6.361 % | 6.312 % | 6.437 % |
| Busiest logical CPU | 99.557 % | 79.798 % | 100.000 % |
| RAM used | 4.286 GiB | 4.187 GiB | 4.461 GiB |
| RAM available | 58.339 GiB | 58.164 GiB | 58.438 GiB |
| File cache | 21.255 GiB | 21.255 GiB | 21.255 GiB |
| Anonymous RAM | 0.611 GiB | 0.593 GiB | 0.828 GiB |
| Swap used | 0.000 GiB | 0.000 GiB | 0.000 GiB |
| Memory pressure avg10 | 0.000 % | 0.000 % | 0.000 % |
| CPU package temperature | 61.193 °C | 57.000 °C | 66.000 °C |
| GPU power | 364.379 W | 250.820 W | 389.890 W |
| GPU utilization | 95.649 % | 36.000 % | 100.000 % |
| GPU VRAM | 21.205 GiB | 21.205 GiB | 21.205 GiB |
| GPU temperature | 61.333 °C | 55.000 °C | 64.000 °C |

### Workload counter changes

- `oom_kill_since_start`: 0.0
- `pgmajfault_since_start`: 0.0
- `psi_cpu_full_stall_us_since_start`: 0.0
- `psi_cpu_some_stall_us_since_start`: 6951.0
- `psi_io_full_stall_us_since_start`: 5757.0
- `psi_io_some_stall_us_since_start`: 5765.0
- `psi_memory_full_stall_us_since_start`: 0.0
- `psi_memory_some_stall_us_since_start`: 0.0
- `pswpin_since_start`: 0.0
- `pswpout_since_start`: 0.0
- Thermal-throttle counters: unchanged.

Counter differences approximate workload boundaries. Shared thermal
counters are not summed. Synthetic generation speed does not represent
Hermes coding speed, and this is not yet a long-duration load test.

Session evidence: `/home/nispoe/graystone/ai-stores/vault/graystone/performance/v1/sessions/daedalus-01/20260908T043748Z-paired-170dc675`

## Paired direct inference — 122880 tokens, 04:41 UTC

- Input: 122880 tokens; output: 512; cached prompt tokens: zero.
- Total request: 117.612 seconds.
- Prompt processing: 115.820 seconds, 1060.954 tokens/s.
- Generation: 1.763 seconds, 289.779 tokens/s.
- Draft acceptance: 478/494.
- Operator wall observations: 437 W and 496 W; average unknown.
- Active samples: 118; full capture: 160 samples.

| Measurement | Sample mean | Minimum | Maximum |
| --- | --- | --- | --- |
| Aggregate CPU busy | 6.358 % | 6.258 % | 6.433 % |
| Busiest logical CPU | 95.943 % | 52.000 % | 100.000 % |
| RAM used | 4.348 GiB | 4.225 GiB | 4.519 GiB |
| RAM available | 58.277 GiB | 58.106 GiB | 58.400 GiB |
| File cache | 21.255 GiB | 21.255 GiB | 21.255 GiB |
| Anonymous RAM | 0.638 GiB | 0.623 GiB | 0.876 GiB |
| Swap used | 0.000 GiB | 0.000 GiB | 0.000 GiB |
| Memory pressure avg10 | 0.000 % | 0.000 % | 0.000 % |
| CPU package temperature | 64.203 °C | 53.000 °C | 69.000 °C |
| GPU power | 364.840 W | 161.980 W | 389.070 W |
| GPU utilization | 94.229 % | 32.000 % | 100.000 % |
| GPU VRAM | 21.205 GiB | 21.205 GiB | 21.205 GiB |
| GPU temperature | 62.941 °C | 52.000 °C | 66.000 °C |

### Workload counter changes

- `oom_kill_since_start`: 0.0
- `pgmajfault_since_start`: 0.0
- `psi_cpu_full_stall_us_since_start`: 0.0
- `psi_cpu_some_stall_us_since_start`: 29730.0
- `psi_io_full_stall_us_since_start`: 7841.0
- `psi_io_some_stall_us_since_start`: 7946.0
- `psi_memory_full_stall_us_since_start`: 0.0
- `psi_memory_some_stall_us_since_start`: 0.0
- `pswpin_since_start`: 0.0
- `pswpout_since_start`: 0.0
- Thermal-throttle counters: unchanged.

Counter boundaries are approximate. Wall readings are individual
observations, not a measured average or guaranteed maximum.
This synthetic test verifies request capacity and execution, not
long-context answer quality or minimum physical RAM requirements.

Session evidence: `/home/nispoe/graystone/ai-stores/vault/graystone/performance/v1/sessions/daedalus-01/20260908T044139Z-paired-601bc7e1`

## Checkpoint — testing paused pending logging plug

The operator purchased a Shelly Plug US Gen4, expected the following day.
Performance testing is paused pending its arrival and wall-power integration.

### Findings so far

- Initial loaded-server idle wall observations: 78.1–80.6 W.
- Highest manually reported whole-machine workload reading: 504 W.
- Hermes performed file editing and terminal test execution.
- One Hermes run failed during final summarization with a peg-native format
  error despite returning exit code zero; a subsequent run completed normally.
- Direct inference completed inputs of 8192, 32768, 65536, and 122880 tokens,
  each generating 512 tokens without reported prompt-cache reuse.
- Live context was changed from 65536 to 131072 during the session.
- At 122880 input tokens, measured RAM usage peaked at 4.519 GiB,
  GPU VRAM remained at 21.205 GiB, and minimum available RAM was 58.106 GiB.
- File cache was approximately 21.255 GiB. Low MemTotal-minus-MemAvailable
  usage does not establish that a small physical RAM configuration performs
  equally well.
- Approximately one logical CPU remained busy; most aggregate CPU capacity
  was unused. The busy thread's function has not been established.
- No memory stalls, swap activity, or thermal-throttle counter increases
  were recorded in the reviewed instrumented workloads.
- Synthetic generation strongly favored speculative drafting; its throughput
  is not a Hermes coding benchmark or a long-context quality evaluation.

### Saved tooling

- `scripts/performance-machine`: target CPU/RAM/GPU telemetry.
- `scripts/performance-hermes`: bounded coding workload.
- `scripts/performance-inference`: fixed-size direct inference workload.
- `scripts/performance-test`: coordinated inference and telemetry capture.

Raw evidence remains outside Git in:
`~/graystone/ai-stores/vault/graystone/performance/v1/`

Git preserves the tooling and this report, not the raw evidence. Preserve
the vault through the existing backup workflow. Generated Hermes projects
remain in target temporary directories and have not been archived.

### Resume plan

1. Configure the plug and verify local access, measurement refresh rate,
   timestamps, and wall-power/current logging.
2. Integrate wall readings into the coordinated test runner.
3. Strengthen Hermes completion checks; exit code zero alone is insufficient.
4. Run sustained workloads with continuous telemetry and no cooling gaps.
5. Compare controlled CPU and RAM limits, including cold model startup.
6. Measure combined CPU/GPU loading after accounting for the circuit rating
   and other equipment sharing the circuit.

### Limits of validation

Telemetry, the CPU/RAM extension, and coordinated direct-inference capture
were exercised on Daedalus. This work did not perform a provisioning
regression, establish minimum hardware requirements, or determine maximum
electrical draw. Meter cadence, CPU package power, and shared-circuit capacity
remain unverified.

## Performance session storage by machine

Performance sessions are now stored under:
`vault/graystone/performance/v1/sessions/<machine-id>/<session-id>/`

The primary identifier is the AI Forge machine ID, such as `daedalus-01`.
Existing sessions were migrated using the machine field in each session.json.
Results and workloads already use machine-specific directories.

Existing session IDs and raw measurement contents are preserved. Absolute paths
printed in historical console logs describe the original locations and are
retained as historical evidence. Telemetry/workload paths in session manifests
remain valid because those directories were not moved.

This change organizes session storage; it does not add new hardware inventory
or configuration measurements.
