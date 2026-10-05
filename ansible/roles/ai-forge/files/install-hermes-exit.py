#!/usr/bin/env python3
from pathlib import Path
import os
import pwd
import shutil
import subprocess

base = Path("/opt/ai-forge/hermes-agent/0.20.6")
source = base / "source"
app = source / "ui-tui/src/app/useMainApp.ts"
module = source / "ui-tui/src/app/forgeExit.ts"
directory = Path("/run/ai-forge-hermes-exit")

account = pwd.getpwnam("daedalus")
directory.mkdir(mode=0o700, exist_ok=True)
os.chown(directory, account.pw_uid, account.pw_gid)
directory.chmod(0o700)

module_text = r"""import {
  existsSync, readFileSync, writeFileSync, unlinkSync
} from 'node:fs'

// AI Forge: request normal exit only after the active response finishes.
export function watchForgeExit(
  idle: () => boolean,
  exit: () => void
): () => void {
  const directory = '/run/ai-forge-hermes-exit'
  if (!existsSync(directory)) return () => {}

  const stat = readFileSync('/proc/self/stat', 'utf8')
  const start = stat.slice(stat.lastIndexOf(')') + 2).split(/\s+/)[19]
  const prefix = `${directory}/${process.pid}-${start}`
  const registration = `${prefix}.json`
  writeFileSync(registration, JSON.stringify({
    pid: process.pid, start, protocol: 1
  }), { mode: 0o600 })

  let closing = false
  const timer = setInterval(() => {
    if (closing || !existsSync(`${prefix}.request`) || !idle()) return
    const token = readFileSync(`${prefix}.request`, 'utf8').trim()
    if (!/^[0-9a-f]{32}$/.test(token)) return
    closing = true
    writeFileSync(`${prefix}.ready`, token, { mode: 0o600 })
    clearInterval(timer)
    exit()
  }, 200)

  return () => {
    clearInterval(timer)
    try { unlinkSync(registration) } catch {}
  }
}
"""

text = app.read_text()
marker = "// AI_FORGE_EXIT_HANDSHAKE_V1"
anchor = "  const dieWithCode = useCallback("
addition = """  // AI_FORGE_EXIT_HANDSHAKE_V1
  useEffect(() => watchForgeExit(
    () => Boolean(getUiState().sid) && !getUiState().busy,
    die
  ), [die])

"""

if marker not in text:
    if text.count(anchor) != 1:
        raise SystemExit("Unexpected Hermes source; no patch applied.")
    backup = app.with_name(app.name + ".ai-forge-original")
    if not backup.exists():
        shutil.copy2(app, backup)
    text = "import { watchForgeExit } from './forgeExit.js'\n" + text
    text = text.replace(anchor, addition + anchor)

changed = (
    app.read_text() != text
    or not module.exists()
    or module.read_text() != module_text
)
app.write_text(text)
module.write_text(module_text)

# Build with the pinned Node installation; no package downloads.
env = os.environ.copy()
env["PATH"] = str(base / "node/bin") + ":" + env.get("PATH", "")
subprocess.run(
    [str(base / "node/bin/node"), "scripts/build.mjs"],
    cwd=source / "ui-tui", env=env, check=True
)

built = source / "ui-tui/dist/entry.js"
if "AI Forge: request normal exit" not in built.read_text():
    # Comments may be removed, but the request-directory literal must remain.
    if "/run/ai-forge-hermes-exit" not in built.read_text():
        raise SystemExit("Built bundle does not contain the exit handshake.")

# Packaged Hermes may prefer this prebuilt location.
packaged = source / "hermes_cli/tui_dist/entry.js"
if packaged.exists():
    shutil.copy2(built, packaged)

print("Hermes exit handshake installed. Start a new TUI session to use it.")
