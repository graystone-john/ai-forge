"""Argus MCP bridge to the existing Athena Hermes profile."""

import os
import re
import subprocess

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("graystone-hermes")


def _ask_hermes(profile: str, workspace: str, task: str, session_id: str = "", remote: bool = False) -> dict:
    """Ask the Athena Hermes specialist to perform a bounded task.

    Starts a new Athena session, or resumes the exact session_id supplied.
    Omit session_id on the first call; reuse the returned ID for follow-ups.
    Uses Athena's existing profile, tools, and rules.
    Returns the real process output, session ID, and exit status.
    An exit status of zero means the process finished, not that the
    requested task was independently verified. Review the response.
    Use read-only tasks during initial integration testing.
    Calls may take up to 150 seconds.
    """
    if not task.strip():
        return {"status": "invalid_request", "error": "Task must not be empty."}

    command = [
        "/usr/bin/timeout", "--signal=TERM", "--kill-after=10s", "140s",
        "/home/nispoe/.local/bin/hermes", "--profile", profile, "chat",
        "--quiet", "--max-turns", "4", "--run-budget", "120",
        "--in", workspace,
        "--query-file", "-",
    ]

    if session_id:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", session_id):
            return {"status": "invalid_request", "error": "Invalid session ID."}
        if session_id == "latest":
            return {"status": "invalid_request", "error": "Supply the exact session ID."}
        command.extend(["--resume", session_id, "--no-restore-cwd"])

    if remote:
        import shlex

        # Run timeout under the same OS user as the remote Hermes process.
        remote_command = [
            "/usr/bin/sudo", "-n", "-H", "-u", "daedalus",
            "/usr/bin/timeout", "--signal=TERM", "--kill-after=10s", "140s",
            "/usr/local/bin/hermes",
            *command[5:],
        ]
        command = [
            "/usr/bin/timeout", "--signal=TERM", "--kill-after=10s", "170s",
            "/usr/bin/ssh", "-T",
            "-i", "/home/nispoe/graystone/ai-forge/secrets/ssh/id_ed25519_ai_forge",
            "-o", "BatchMode=yes",
            "-o", "IdentitiesOnly=yes",
            "-o", "StrictHostKeyChecking=yes",
            "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=3",
            "ai-forge@10.10.10.21",
            shlex.join(remote_command),
        ]

    # Hermes loads its own profile credentials; it needs no Turnstone secrets.
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith("TURNSTONE_")
    }

    try:
        result = subprocess.run(
            command,
            input=task,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            cwd="/home/nispoe/graystone/ai-forge" if remote else workspace,
        )
    except OSError as exc:
        return {"status": "launch_failed", "error": str(exc)}

    match = re.search(
        r"(?m)^\s*session_id:\s*(\S+)\s*$", result.stderr + "\n" + result.stdout
    )
    return {
        "profile": profile,
        "host": "10.10.10.21" if remote else "local",
        "status": (
            "process_finished" if result.returncode == 0
            else "timed_out" if result.returncode in (124, 137)
            else "process_failed"
        ),
        "exit_status": result.returncode,
        "session_id": match.group(1) if match else None,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }



@mcp.tool()
def ask_athena(task: str, session_id: str = "") -> dict:
    """Delegate a bounded task to Athena Hermes in the ai-forge workspace.

    Omit session_id for a new conversation; reuse Athena's returned ID
    for follow-ups. Returns real stdout, stderr, session_id and exit_status.
    Up to four tool iterations and a 120-second run budget per call.
    Calls may take 150 seconds. Use read-only tasks during initial testing.
    Process success alone does not establish task completion.
    """
    return _ask_hermes(
        "athena", "/home/nispoe/graystone/ai-forge", task, session_id
    )


@mcp.tool()
def ask_nemosyne(task: str, session_id: str = "") -> dict:
    """Delegate an ai-stores task to the Nemosyne Hermes specialist.

    Specializes in artifact acquisition, cataloging, provenance,
    integrity, preservation and offline distribution.
    Runs in /home/nispoe/graystone/ai-stores using its existing profile.
    Omit session_id initially; reuse Nemosyne's returned ID for follow-ups.
    Returns real stdout, stderr, session_id and exit_status.
    Up to four tool iterations and a 120-second run budget per call.
    Calls may take 150 seconds. Use read-only tasks during initial testing.
    Process success alone does not establish task completion.
    """
    return _ask_hermes(
        "nemosyne", "/home/nispoe/graystone/ai-stores", task, session_id
    )



@mcp.tool()
def ask_daedalus(task: str, session_id: str = "") -> dict:
    """Delegate a task to the Daedalus Hermes agent on Daedalus-02.

    Executes on 10.10.10.21 as OS user daedalus, using Hermes profile
    daedalus and workspace /home/daedalus/graystone/ai-forge.
    Omit session_id initially; reuse Daedalus's returned ID for follow-ups.
    Never use another specialist's session ID.
    Returns actual host, profile, stdout, stderr, session_id and exit_status.
    Four tool iterations and a 120-second run budget per call.
    Including SSH and shutdown time, calls may take up to 180 seconds.
    Use read-only tasks during initial testing.
    Process success alone does not establish task completion.
    """
    return _ask_hermes(
        "daedalus", "/home/daedalus/graystone/ai-forge",
        task, session_id, remote=True
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
