#!/usr/bin/env python3
"""
claude-usage-bar — Claude Code usage in your Mac menu bar.
https://github.com/YOUR_USERNAME/claude-usage-bar
"""

import rumps
import json
import re
import glob
import threading
import subprocess
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from pathlib import Path
import pwd
import os

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Hide dock icon — menu bar only
try:
    import AppKit
    info = AppKit.NSBundle.mainBundle().infoDictionary()
    info["LSUIElement"] = "1"
except Exception:
    pass

CLAUDE_DIR = Path.home() / ".claude"
REFRESH_INTERVAL = 60
SESSION_WINDOW_HOURS = 5


def local_now():
    return datetime.now().astimezone()


def fmt_time(dt):
    """Format a datetime in the user's local timezone."""
    local = dt.astimezone()
    return local.strftime("%-I:%M %p %Z")


# ── Token discovery ───────────────────────────────────────────────────────────

def get_oauth_token():
    """
    Auto-discover the Claude Code OAuth token from macOS Keychain.

    Strategy (in order):
    1. Read "Claude Code-credentials" without specifying account — works regardless
       of what username Claude Code used when it stored the token (the #1 failure
       cause on fresh Macs where the stored account differs from current user).
    2. Read same service with current username as fallback.
    3. Check "com.amirhayek.ClaudeUsage.oauth-cache" — the 'Usage for Claude' app
       caches a validated token here; reuse it if present.
    4. Check credential JSON files on disk.

    Token expiry: if expiresAt is in the past by more than 5 min, attempt a
    silent refresh by invoking the Claude CLI (which updates the keychain), then
    re-read once.
    """
    token, expires_at = _read_best_token()

    if token and expires_at:
        now_ms = datetime.now(timezone.utc).timestamp() * 1000
        # Token expired — try a silent refresh via Claude CLI
        if now_ms > expires_at + 5 * 60 * 1000:
            _try_silent_refresh()
            token, expires_at = _read_best_token()

    return token


def _read_best_token():
    """Return (access_token, expires_at_ms) from the best available source."""
    username = pwd.getpwuid(os.getuid()).pw_name

    # Primary: "Claude Code-credentials" — try without account first, then with
    for account in [None, username, ""]:
        raw = _keychain_read("Claude Code-credentials", account)
        if raw:
            tok, exp = _extract_oauth_token(raw)
            if tok:
                return tok, exp

    # Secondary: 'Usage for Claude' app oauth cache
    raw = _keychain_read("com.amirhayek.ClaudeUsage.oauth-cache", "claude_code_token")
    if raw:
        tok, exp = _extract_oauth_token(raw)
        if tok:
            return tok, exp

    # Tertiary: credential files on disk
    for p in [
        CLAUDE_DIR / ".credentials.json",
        CLAUDE_DIR / "credentials.json",
        Path.home() / "Library/Application Support/Claude/credentials.json",
    ]:
        tok, exp = _token_from_json_file(p)
        if tok:
            return tok, exp

    return None, None


def _extract_oauth_token(raw):
    """Parse a raw keychain string and return (access_token, expires_at_ms)."""
    try:
        blob = json.loads(raw)
        oauth = blob.get("claudeAiOauth", {})
        token = oauth.get("accessToken", "")
        expires = oauth.get("expiresAt")  # milliseconds epoch
        if token and _looks_like_token(token):
            return token, expires
        # Fallback: walk all values
        for val in _flatten_values(blob):
            if isinstance(val, str) and _looks_like_token(val):
                return val, None
    except Exception:
        pass
    if _looks_like_token(raw):
        return raw, None
    return None, None


def _try_silent_refresh():
    """Ask the Claude CLI to run a no-op so it refreshes the keychain token."""
    try:
        subprocess.run(
            ["claude", "--version"],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass


def _keychain_read(service, account):
    try:
        cmd = ["security", "find-generic-password", "-s", service, "-w"]
        if account is not None and account != "":
            cmd += ["-a", account]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        val = r.stdout.strip()
        return val if r.returncode == 0 and val else None
    except Exception:
        return None


def _token_from_json_file(path):
    try:
        data = json.loads(Path(path).read_text())
        oauth = data.get("claudeAiOauth", {})
        token = oauth.get("accessToken", "")
        expires = oauth.get("expiresAt")
        if token and _looks_like_token(token):
            return token, expires
        for val in _flatten_values(data):
            if isinstance(val, str) and _looks_like_token(val):
                return val, None
    except Exception:
        pass
    return None, None


def _flatten_values(obj, depth=0):
    if depth > 8:
        return
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _flatten_values(v, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            yield from _flatten_values(v, depth + 1)
    else:
        yield obj


def _looks_like_token(s):
    if not isinstance(s, str) or len(s) < 20:
        return False
    if s.startswith("sk-ant-"):
        return True
    if len(s) > 80 and re.match(r'^[A-Za-z0-9_\-\.]+$', s):
        return True
    if s.count('.') == 2 and len(s) > 60:  # JWT
        return True
    return False


# ── Live usage API ─────────────────────────────────────────────────────────────

def fetch_live_usage():
    """
    Fetch session/weekly usage % from Anthropic's internal OAuth endpoint.
    Discovered by the community: https://github.com/anthropics/claude-code/issues/27915
    """
    if not HAS_REQUESTS:
        return None, "requests not installed"

    token = get_oauth_token()
    if not token:
        return None, "token not found — run 'claude' once to authenticate"

    try:
        r = requests.get(
            "https://api.anthropic.com/api/oauth/usage",
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            five  = data.get("five_hour") or data.get("session") or {}
            seven = data.get("seven_day")  or data.get("weekly")  or {}
            session_pct = five.get("utilization")  or five.get("used_percentage")
            weekly_pct  = seven.get("utilization") or seven.get("used_percentage")
            resets_at   = five.get("resets_at", "")
            resets_str  = ""
            if resets_at:
                try:
                    rt = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
                    resets_str = fmt_time(rt)
                except Exception:
                    pass
            return {
                "session_pct": round(float(session_pct)) if session_pct is not None else None,
                "weekly_pct":  round(float(weekly_pct))  if weekly_pct  is not None else None,
                "resets_str":  resets_str,
                "raw":         data,
            }, "ok"
        elif r.status_code == 401:
            return None, "401 — token expired, re-run 'claude' to refresh"
        else:
            return None, f"HTTP {r.status_code}"
    except Exception as e:
        return None, str(e)[:80]


# ── JSONL parsing ─────────────────────────────────────────────────────────────

def parse_current_session():
    """Parse ~/.claude/projects/**/*.jsonl for the last SESSION_WINDOW_HOURS."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=SESSION_WINDOW_HOURS)
    files  = glob.glob(str(CLAUDE_DIR / "projects" / "**" / "*.jsonl"), recursive=True)

    models = defaultdict(int)
    total_input = total_output = total_cache_read = total_cache_write = 0
    tool_calls  = defaultdict(int)
    timestamps  = []

    for fpath in files:
        try:
            with open(fpath, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    ts_str = r.get("timestamp", "")
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            if ts < cutoff:
                                continue
                            timestamps.append(ts)
                        except Exception:
                            pass
                    if r.get("type") == "assistant":
                        msg = r.get("message", {})
                        if not isinstance(msg, dict):
                            continue
                        model = msg.get("model", "")
                        if model and model != "<synthetic>":
                            models[model] += 1
                        u = msg.get("usage", {})
                        total_input       += u.get("input_tokens", 0)
                        total_output      += u.get("output_tokens", 0)
                        total_cache_read  += u.get("cache_read_input_tokens", 0)
                        total_cache_write += u.get("cache_creation_input_tokens", 0)
                        for block in (msg.get("content") or []):
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                tool_calls[block.get("name", "?")] += 1
        except Exception:
            continue

    duration_str = ""
    if timestamps:
        first, last = min(timestamps), max(timestamps)
        h, rem = divmod(int((last - first).total_seconds()), 3600)
        duration_str = f"{h}h {rem // 60}m"

    now_local = local_now().strftime("%H:%M %Z")

    return {
        "models":            dict(models),
        "total_responses":   sum(models.values()),
        "total_output":      total_output,
        "total_cache_read":  total_cache_read,
        "total_cache_write": total_cache_write,
        "total_input":       total_input,
        "top_tools":         sorted(tool_calls.items(), key=lambda x: -x[1])[:3],
        "duration":          duration_str,
        "last_updated":      now_local,
    }


def estimate_cost(s):
    """Rough gross cost estimate using Opus 4 public pricing."""
    return (
        s["total_input"]       / 1e6 * 15.0
      + s["total_output"]      / 1e6 * 75.0
      + s["total_cache_write"] / 1e6 * 18.75
      + s["total_cache_read"]  / 1e6 * 1.50
    )


# ── Menu bar app ──────────────────────────────────────────────────────────────

class ClaudeUsageApp(rumps.App):
    def __init__(self):
        super().__init__("☁", quit_button=None)
        self.live  = None
        self.stats = None
        self.error = ""

        self.status_item    = rumps.MenuItem("Loading…")
        self.token_item     = rumps.MenuItem("")
        self.session_item   = rumps.MenuItem("Session: —")
        self.weekly_item    = rumps.MenuItem("Weekly: —")
        self.resets_item    = rumps.MenuItem("")
        self.model_item     = rumps.MenuItem("Models: —")
        self.responses_item = rumps.MenuItem("Responses: —")
        self.output_item    = rumps.MenuItem("Output: —")
        self.cache_item     = rumps.MenuItem("Cache reads: —")
        self.tools_item     = rumps.MenuItem("Top tools: —")
        self.cost_item      = rumps.MenuItem("Est. cost: —")
        self.duration_item  = rumps.MenuItem("Duration: —")
        self.refresh_item   = rumps.MenuItem("Refresh now",      callback=self.refresh_now)
        self.dashboard_item = rumps.MenuItem("Open claude.ai →", callback=self.open_dashboard)
        self.debug_item     = rumps.MenuItem("Debug info…",      callback=self.show_debug)
        self.quit_item      = rumps.MenuItem("Quit",             callback=rumps.quit_application)

        self.menu = [
            self.status_item, self.token_item,
            self.session_item, self.weekly_item, self.resets_item, None,
            self.model_item, self.responses_item, self.output_item,
            self.cache_item, self.tools_item, self.cost_item, self.duration_item, None,
            self.refresh_item, self.dashboard_item, self.debug_item, None,
            self.quit_item,
        ]
        self._refresh()

    @rumps.timer(REFRESH_INTERVAL)
    def refresh_timer(self, _):
        threading.Thread(target=self._refresh, daemon=True).start()

    def _refresh(self):
        self.stats         = parse_current_session()
        self.live, self.error = fetch_live_usage()
        self._update_menu()

    def _update_menu(self):
        s, live = self.stats, self.live
        cost = estimate_cost(s)

        if live and live.get("session_pct") is not None:
            pct = live["session_pct"]
            self.title              = f"☁ {pct}%"
            self.session_item.title = f"Session:  {self._bar(pct)}  {pct}%"
            self.token_item.title   = "Token: ✅  auto-detected"
        else:
            self.title              = f"☁ {s['total_responses']}↑"
            self.session_item.title = f"Session: — ({self.error})"
            self.token_item.title   = f"Token: ❌  {self.error}"

        wpct = live.get("weekly_pct") if live else None
        self.weekly_item.title = f"Weekly:   {self._bar(wpct)}  {wpct}%" if wpct is not None else "Weekly: —"

        resets = live.get("resets_str", "") if live else ""
        self.resets_item.title = f"Resets at {resets}" if resets else ""
        self.status_item.title = f"Updated {s['last_updated']}"

        models_str = "  |  ".join(
            f"{m.replace('claude-','')}: {c}"
            for m, c in sorted(s["models"].items(), key=lambda x: -x[1])
        )
        self.model_item.title     = f"Models: {models_str or '—'}"
        self.responses_item.title = f"Responses: {s['total_responses']:,}"
        self.output_item.title    = f"Output: {s['total_output']:,} tokens"
        self.cache_item.title     = f"Cache reads: {s['total_cache_read']/1e6:.1f}M tokens"
        top = ", ".join(f"{n}({c})" for n, c in s["top_tools"]) or "—"
        self.tools_item.title    = f"Top tools: {top}"
        self.cost_item.title     = f"Est. cost: ${cost:.2f} (gross)"
        self.duration_item.title = f"Session window: {s['duration'] or '—'}"

    def _bar(self, pct, width=10):
        filled = round((pct or 0) / 100 * width)
        return "█" * filled + "░" * (width - filled)

    def refresh_now(self, _):
        threading.Thread(target=self._refresh, daemon=True).start()

    def open_dashboard(self, _):
        subprocess.Popen(["open", "https://claude.ai/settings/usage"])

    def show_debug(self, _):
        username = pwd.getpwuid(os.getuid()).pw_name
        # Try all sources for debug visibility
        raw_no_acct = _keychain_read("Claude Code-credentials", None) or "NOT FOUND"
        raw_with_acct = _keychain_read("Claude Code-credentials", username) or "NOT FOUND"
        token, expires_at = _read_best_token()
        exp_str = ""
        if expires_at:
            try:
                exp_str = datetime.fromtimestamp(expires_at / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            except Exception:
                exp_str = str(expires_at)
        msg = (
            f"Keychain (no account): {len(raw_no_acct)} chars\n"
            f"Keychain ({username}): {len(raw_with_acct)} chars\n\n"
            f"Token found: {'YES — ' + str(len(token)) + ' chars' if token else 'NO'}\n"
            f"Token preview: {token[:25] + '…' if token else '—'}\n"
            f"Token expires: {exp_str or '—'}\n\n"
            f"API error: {self.error or 'none'}\n\n"
            f"Raw API response:\n{json.dumps(self.live.get('raw') if self.live else {}, indent=2)[:500]}"
        )
        rumps.alert(title="Debug Info", message=msg)


def main():
    ClaudeUsageApp().run()


if __name__ == "__main__":
    main()