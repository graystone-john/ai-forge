"""Read-only Shelly polling for performance captures."""
import datetime
import json
import math
import threading
import time
import urllib.request


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class ShellyRecorder:
    def __init__(self, address, directory):
        self.address = address
        self.directory = directory
        self.url = f"http://{address}/rpc/Switch.GetStatus?id=0"
        # Local device access must not go through an HTTP proxy.
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({})
        )
        self.halt = threading.Event()
        self.thread = None
        self.raw = None
        self.attempts = 0
        self.errors = 0
        self.readings = []
        self.started = time.monotonic()

    def sample(self):
        begin = time.monotonic()
        event = {
            "type": "shelly_sample",
            "request_started_utc": utc(),
            "elapsed_seconds": begin - self.started,
        }
        valid = False
        try:
            with self.opener.open(self.url, timeout=3) as response:
                data = json.load(response)
            event["response"] = data
            power = data.get("apower")
            valid = (
                data.get("id") == 0
                and data.get("output") is True
                and isinstance(power, (int, float))
                and not isinstance(power, bool)
                and math.isfinite(power)
                and power >= 0
            )
            if not valid:
                raise ValueError("Expected outlet ON and finite nonnegative apower")
            self.readings.append((begin, float(power)))
        except Exception as exc:
            self.errors += 1
            event["error"] = f"{type(exc).__name__}: {exc}"
        event["response_received_utc"] = utc()
        event["request_seconds"] = time.monotonic() - begin
        event["valid"] = valid
        self.attempts += 1
        self.raw.write(json.dumps(event, allow_nan=False) + "\n")
        self.raw.flush()
        return valid

    def start(self):
        self.raw = (self.directory / "shelly.jsonl").open("x")
        self.raw.write(json.dumps({
            "type": "metadata",
            "timestamp_utc": utc(),
            "address": self.address,
            "endpoint": "Switch.GetStatus?id=0",
            "requested_interval_seconds": 1,
            "http_timeout_seconds": 3,
            "timestamp_source": "Athena",
        }) + "\n")
        self.raw.flush()
        if not self.sample():
            self.stop()
            raise RuntimeError(
                "Shelly initial reading failed; see shelly.jsonl"
            )
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def loop(self):
        try:
            next_poll = time.monotonic() + 1.0
            while True:
                if self.halt.wait(max(0.0, next_poll - time.monotonic())):
                    break
                self.sample()
                next_poll += 1.0
                now = time.monotonic()
                if next_poll <= now:
                    # Skip missed deadlines; never burst to catch up.
                    next_poll += math.floor(now - next_poll) + 1
        except Exception as exc:
            self.errors += 1
            self.worker_error = f"{type(exc).__name__}: {exc}"

    def stop(self):
        self.halt.set()
        if self.thread is not None:
            self.thread.join()
            self.thread = None
        if self.raw is not None:
            self.raw.close()
            self.raw = None
        powers = [power for _, power in self.readings]
        gaps = [
            b[0] - a[0]
            for a, b in zip(self.readings, self.readings[1:])
        ]
        result = {
            "status": (
                "completed" if powers and not self.errors else "degraded"
            ),
            "address": self.address,
            "attempts": self.attempts,
            "valid_samples": len(powers),
            "error_samples": self.errors,
            "worker_error": getattr(self, "worker_error", None),
            "power_w": {
                "min": min(powers) if powers else None,
                "sample_mean": sum(powers) / len(powers) if powers else None,
                "max": max(powers) if powers else None,
            },
            "max_valid_sample_gap_seconds": max(gaps) if gaps else None,
            "definitions": {
                "scope": "Entire capture, including idle and recovery",
                "mean": "Arithmetic sample mean, not time-weighted",
                "peak": "Observed reading maximum, not transient maximum",
                "timing": "Athena request timestamps; sensor update time unknown",
                "energy": "Original aenergy fields preserved in raw responses",
                "temperature": "Plug internal temperature, not CPU temperature",
                "errors": "Missing or invalid readings are not replaced with zero",
            },
        }
        (self.directory / "shelly-summary.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        return result
