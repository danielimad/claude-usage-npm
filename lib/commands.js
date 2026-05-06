"use strict";

const { execSync, spawnSync } = require("child_process");
const fs   = require("fs");
const path = require("path");
const os   = require("os");

const HOME       = os.homedir();
const DEST       = path.join(HOME, ".claude-usage-bar");
const VENV       = path.join(DEST, "venv");
const PYTHON     = path.join(VENV, "bin", "python3");
const ENTRY      = path.join(VENV, "bin", "claude-usage-bar");
const APP_PY     = path.join(DEST, "app.py");
const PLIST_PATH = path.join(HOME, "Library", "LaunchAgents", "com.claude.usagebar.plist");
const PLIST_LABEL = "com.claude.usagebar";

// ── helpers ──────────────────────────────────────────────────────────────────

function run(cmd, opts = {}) {
  return spawnSync("bash", ["-c", cmd], { stdio: "inherit", ...opts });
}

function silent(cmd) {
  return spawnSync("bash", ["-c", cmd], { stdio: "pipe" });
}

function ok(msg)   { console.log(`  ✅  ${msg}`); }
function err(msg)  { console.log(`  ❌  ${msg}`); }
function info(msg) { console.log(`  →   ${msg}`); }
function header(msg) {
  console.log("");
  console.log(`  ☁  ${msg}`);
  console.log("  " + "─".repeat(40));
}

function checkMac() {
  if (os.platform() !== "darwin") {
    err("claude-usage only works on macOS");
    process.exit(1);
  }
}

function findPython3() {
  for (const p of ["python3", "/usr/local/bin/python3", "/opt/homebrew/bin/python3"]) {
    const r = silent(`${p} --version`);
    if (r.status === 0) return p;
  }
  return null;
}

function fetchFile(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      if (res.statusCode === 301 || res.statusCode === 302) {
        return fetchFile(res.headers.location).then(resolve).catch(reject);
      }
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => resolve(data));
    }).on("error", reject);
  });
}

function writePlist() {
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>${APP_PY}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>LSUIElement</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>${path.join(DEST, "error.log")}</string>
    <key>StandardOutPath</key>
    <string>${path.join(DEST, "out.log")}</string>
</dict>
</plist>`;
  fs.mkdirSync(path.dirname(PLIST_PATH), { recursive: true });
  fs.writeFileSync(PLIST_PATH, xml);
}

function isRunning() {
  const r = silent(`launchctl list | grep ${PLIST_LABEL}`);
  return r.status === 0 && r.stdout.toString().trim().length > 0;
}

// ── commands ──────────────────────────────────────────────────────────────────

async function install() {
  checkMac();
  header("Installing claude-usage-bar");

  // 1. Python
  const py = findPython3();
  if (!py) {
    err("Python 3 not found. Install with: brew install python");
    process.exit(1);
  }
  ok(`Python found (${py})`);

  // 2. Create dest + venv
  fs.mkdirSync(DEST, { recursive: true });
  info("Creating virtual environment…");
  run(`${py} -m venv "${VENV}"`);
  ok("Virtual environment ready");

  // 3. Install Python package from GitHub
  info("Installing Python dependencies…");
  run(`"${VENV}/bin/pip" install --quiet --upgrade pip`);
  run(`"${VENV}/bin/pip" install --quiet rumps requests`);
  ok("Dependencies installed");

  // 4. Copy bundled app.py
  info("Installing app…");
  const bundledApp = path.join(__dirname, "app.py");
  fs.copyFileSync(bundledApp, APP_PY);
  ok("App installed");

  // 5. Stop any existing instance
  silent(`launchctl unload "${PLIST_PATH}" 2>/dev/null`);

  // 6. Write LaunchAgent plist
  writePlist();
  ok("LaunchAgent created (auto-starts on login and after reboot)");

  // 7. Start it now
  run(`launchctl load "${PLIST_PATH}"`);

  console.log("");
  console.log("  ✅  Done! Look for ☁ in your menu bar.");
  console.log("");
  console.log("  To stop:      claude-usage stop");
  console.log("  To uninstall: claude-usage uninstall");
  console.log("");
}

async function uninstall() {
  checkMac();
  header("Uninstalling claude-usage-bar");
  silent(`launchctl unload "${PLIST_PATH}" 2>/dev/null`);
  if (fs.existsSync(PLIST_PATH)) fs.unlinkSync(PLIST_PATH);
  if (fs.existsSync(DEST)) fs.rmSync(DEST, { recursive: true, force: true });
  ok("Uninstalled successfully");
  console.log("");
}

async function start() {
  checkMac();
  if (!fs.existsSync(PLIST_PATH)) {
    err("Not installed. Run: npx claude-usage install");
    process.exit(1);
  }
  silent(`launchctl unload "${PLIST_PATH}" 2>/dev/null`);
  run(`launchctl load "${PLIST_PATH}"`);
  ok("Started — look for ☁ in your menu bar");
  console.log("");
}

async function stop() {
  checkMac();
  silent(`launchctl unload "${PLIST_PATH}" 2>/dev/null`);
  ok("Stopped (LaunchAgent still installed — will restart on next login)");
  console.log("  To permanently remove: claude-usage uninstall");
  console.log("");
}

async function status() {
  checkMac();
  const installed = fs.existsSync(PLIST_PATH);
  const running   = isRunning();
  const appExists = fs.existsSync(APP_PY);
  console.log("");
  console.log("  ☁  claude-usage-bar status");
  console.log("  " + "─".repeat(40));
  console.log(`  Installed:     ${installed ? "✅  yes" : "❌  no"}`);
  console.log(`  App file:      ${appExists ? "✅  yes" : "❌  missing"}`);
  console.log(`  Running:       ${running   ? "✅  yes" : "❌  no"}`);
  console.log(`  LaunchAgent:   ${PLIST_PATH}`);
  console.log(`  App dir:       ${DEST}`);
  if (fs.existsSync(path.join(DEST, "error.log"))) {
    const log = fs.readFileSync(path.join(DEST, "error.log"), "utf8").trim().slice(-500);
    if (log) {
      console.log("\n  Last errors:");
      console.log(log.split("\n").map(l => `    ${l}`).join("\n"));
    }
  }
  console.log("");
}

module.exports = { install, uninstall, start, stop, status };