#!/usr/bin/env python3

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DATA_ROOT = Path.home() / "graystone" / "provisioning-data"
HTTP_ROOT = DATA_ROOT / "http"
STATE_ROOT = DATA_ROOT / "state"

HOST = "127.0.0.1"
PORT = 8081


class Handler(BaseHTTPRequestHandler):

    def do_GET(self):
        parts = self.path.strip("/").split("/")

        if len(parts) != 2 or parts[0] != "boot":
            self.send_error(404)
            return

        machine = parts[1]

        # Restrict machine names to simple safe characters.
        if not machine.replace("-", "").replace("_", "").isalnum():
            self.send_error(400)
            return

        machine_http = HTTP_ROOT / machine
        state_dir = STATE_ROOT / machine
        state_file = state_dir / "mode"

        if not machine_http.is_dir():
            self.send_error(404, "Unknown machine")
            return

        state_dir.mkdir(parents=True, exist_ok=True)

        try:
            mode = state_file.read_text().strip()
        except FileNotFoundError:
            mode = "normal"

        if mode == "provision":
            #
            # Consume provisioning BEFORE returning provision.ipxe.
            #
            state_file.write_text("normal\n")
            selected = machine_http / "provision.ipxe"
            print(f"{machine}: consumed PROVISION -> NORMAL", flush=True)

        else:
            selected = machine_http / "normal.ipxe"
            print(f"{machine}: NORMAL", flush=True)

        if not selected.is_file():
            self.send_error(500, f"Missing {selected.name}")
            return

        body = selected.read_bytes()

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


HTTPServer((HOST, PORT), Handler).serve_forever()
