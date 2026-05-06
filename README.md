# ☁ claude-usage-bar

> Track your Claude session, weekly usage, and Claude Code stats from the macOS menu bar.

![macOS](https://img.shields.io/badge/macOS-13%2B-lightgrey)
![npm](https://img.shields.io/npm/v/claude-usage-bar)
![License](https://img.shields.io/badge/license-MIT-green)

There are **two distributions** in this repo. Pick whichever fits.

---

## 1. Native macOS app (recommended)

A signed, notarized SwiftUI menu-bar app + full dashboard window.

- ☁ menu-bar icon with live three-bar usage indicator and `N%` label
- **Sign in with Email** flow — no Claude Code CLI required
- **Dashboard window** with: session/weekly cards, current-session chart anchored to your real reset cycle, 5h-session-box history (12h / 24h / 3d / 7d / 30d / 90d filters), 365-day activity heatmap, insights cards, and Claude Code stats (per-project, per-model breakdown with `All / Sonnet / Opus / Haiku` filters, cost estimate)
- Dock-less by default; dock icon shows only while the dashboard window is open
- macOS 13+, universal (Apple Silicon + Intel)

### Install

Download the latest `.dmg` from [`macos/`](./macos/), open it, drag **Claude Usage Bar.app** to Applications, and launch it. The first launch shows a Welcome screen — enter your claude.ai email and sign in.

```
macos/ClaudeUsageBar-0.2.7.dmg
```

The DMG is signed with a Developer ID certificate and notarized by Apple, so it opens cleanly without Gatekeeper warnings.

### Sign-in flow

1. Click ☁ in the menu bar → **Sign in with Email**
2. Enter your claude.ai email
3. A WebView opens, the email is auto-filled, and **Continue with email** is auto-clicked
4. Check your inbox, copy the verification code, paste it in the WebView
5. The window closes automatically once your session cookie lands; usage starts populating

### Claude Code stats

The dashboard reads `~/.claude/projects/**/*.jsonl` to compute per-project messages, tool calls, sessions, tokens, and per-model API-equivalent cost. The first time you open this section the app will ask for read access to `~/.claude/` via a standard macOS file panel.

---

## 2. npm version (Python menu-bar app)

The original CLI-installed Python rumps app. Lighter (no dashboard window, no charts), but useful if you only want the menu-bar percentage and already have Claude Code CLI authenticated.

### Install

```bash
npx claude-usage-bar install
```

`☁ 25%` appears in your menu bar immediately and **auto-starts on every login and reboot**.

### Commands

```bash
npx claude-usage-bar install     # install + start (first time)
claude-usage-bar start           # start the menu bar app
claude-usage-bar stop            # stop it (stays installed, restarts on next login)
claude-usage-bar uninstall       # remove everything
claude-usage-bar status          # show whether it's running
```

### What it shows

- ☁ N% — live session usage in your menu bar
- Session / weekly limit %
- Reset time in your local timezone
- Model breakdown (Opus / Sonnet / Haiku)
- Token counts, cache reads, top tools
- Estimated gross cost

### Requirements

- macOS
- Python 3.9+ (`brew install python` if needed)
- Claude Code installed and authenticated (`claude` once)

The npm version reads its OAuth token from the macOS Keychain entry that Claude Code CLI stores. If you haven't run Claude Code on your machine yet, run it once to authenticate, then start the menu bar.

### Uninstall

```bash
claude-usage-bar uninstall
```

---

## Which one should I install?

| | Native `.dmg` | npm `claude-usage-bar` |
|---|---|---|
| Requires Claude Code CLI | ❌ no | ✅ yes |
| Sign-in | Browser flow | Auto from Keychain |
| Menu bar | ✅ | ✅ |
| Dashboard window | ✅ | ❌ |
| Charts & history | ✅ | ❌ |
| Activity heatmap | ✅ | ❌ |
| Claude Code per-project stats | ✅ (with model filters) | partial |
| Install via Terminal | ❌ (drag-and-drop DMG) | ✅ one command |
| Auto-launch at login | ✅ | ✅ |

If you don't already use Claude Code and just want to track your usage, **install the native `.dmg`**. If you live in the terminal and already have Claude Code authenticated, **the npm version is one command**.

## License

MIT
