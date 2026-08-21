#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import yaml


ROOT = Path.home() / "graystone" / "ai-forge"
DATA_ROOT = Path.home() / "graystone" / "provisioning-data"

MACHINES_ROOT = ROOT / "machines"
HTTP_ROOT = DATA_ROOT / "http"
STATE_ROOT = DATA_ROOT / "state"

HOST = "127.0.0.1"
PORT = 8081


def find_machine_by_mac(mac):
    """
    Look up a registered AI Forge machine by provisioning MAC address.
    """
    mac = mac.strip().lower()

    for machine_file in sorted(MACHINES_ROOT.glob("*/machine.yaml")):
        with machine_file.open("r", encoding="utf-8") as f:
            machine = yaml.safe_load(f)

        machine_mac = (
            machine.get("network", {})
            .get("provisioning_mac", "")
            .strip()
            .lower()
        )

        if machine_mac == mac:
            return machine["name"]

    return None


class Handler(BaseHTTPRequestHandler):

    def send_ipxe(self, path):
        if not path.is_file():
            self.send_error(500, f"Missing boot file: {path.name}")
            return

        body = path.read_bytes()

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        self.wfile.write(body)

    def handle_machine_boot(self, machine):
        """
        Return normal.ipxe or provision.ipxe for a registered machine.

        'provision' is intentionally one-shot:
        state is reset to 'normal' BEFORE provision.ipxe is returned.
        """
        machine_http = HTTP_ROOT / machine
        state_dir = STATE_ROOT / machine
        state_file = state_dir / "mode"

        if not machine_http.is_dir():
            self.send_error(404, f"Unknown machine: {machine}")
            return

        state_dir.mkdir(parents=True, exist_ok=True)

        try:
            mode = state_file.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            mode = "normal"

        if mode == "provision":
            # Consume provisioning before sending the destructive boot script.
            state_file.write_text("normal\n", encoding="utf-8")

            selected = machine_http / "provision.ipxe"

            print(
                f"{machine}: consumed PROVISION -> NORMAL",
                flush=True,
            )

        elif mode == "normal":
            selected = machine_http / "normal.ipxe"

            print(
                f"{machine}: NORMAL",
                flush=True,
            )

        else:
            # Fail safe. Unknown state must never trigger provisioning.
            state_file.write_text("normal\n", encoding="utf-8")

            print(
                f"{machine}: invalid mode '{mode}' -> forcing NORMAL",
                flush=True,
            )

            selected = machine_http / "normal.ipxe"

        self.send_ipxe(selected)

    def do_GET(self):
        parsed = urlparse(self.path)

        #
        # Scalable PXE lookup:
        #
        # /boot-mac?mac=f0:2f:74:d3:34:d2
        #
        # Used by the global iPXE entry script.
        #
        if parsed.path == "/boot-mac":
            params = parse_qs(parsed.query)
            mac = params.get("mac", [""])[0]

            if not mac:
                self.send_error(400, "Missing MAC address")
                return

            machine = find_machine_by_mac(mac)

            if not machine:
                print(
                    f"Unknown PXE client MAC: {mac}",
                    flush=True,
                )

                self.send_error(
                    404,
                    f"Unknown MAC: {mac}",
                )
                return

            print(
                f"PXE MAC {mac} -> {machine}",
                flush=True,
            )

            self.handle_machine_boot(machine)
            return

        #
        # Direct machine endpoint retained for testing/admin use:
        #
        # /boot/daedalus-01
        #
        parts = parsed.path.strip("/").split("/")

        if len(parts) == 2 and parts[0] == "boot":
            machine = parts[1]

            # Restrict machine names to safe characters.
            if not machine.replace("-", "").replace("_", "").isalnum():
                self.send_error(400, "Invalid machine name")
                return

            self.handle_machine_boot(machine)
            return

        self.send_error(404)

    def log_message(self, fmt, *args):
        # Suppress default HTTP request logging.
        return


def main():
    print(
        f"Graystone AI Forge boot controller listening on "
        f"http://{HOST}:{PORT}",
        flush=True,
    )

    HTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
