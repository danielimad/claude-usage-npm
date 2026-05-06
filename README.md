# ☁ claude-usage

> Claude Code usage in your Mac menu bar — session %, weekly %, tokens, models, cost.

![macOS](https://img.shields.io/badge/macOS-only-lightgrey)
![npm](https://img.shields.io/npm/v/claude-usage)
![License](https://img.shields.io/badge/license-MIT-green)

## Install

```bash
npx claude-usage-bar install
```

That's it. `☁ 25%` appears in your menu bar immediately and **auto-starts on every login and reboot** — no manual steps ever again.

## Commands

```bash
npx claude-usage-bar install     # install + start (first time)
claude-usage install         # same, if installed globally

claude-usage start           # start the menu bar app
claude-usage stop            # stop it (stays installed, restarts on next login)
claude-usage uninstall       # remove everything
claude-usage status          # show whether it's running
```

## What it shows

- **☁ 25%** — live session usage % in your menu bar
- Session / Weekly limit %
- When your session resets (your local timezone)
- Models breakdown (Opus / Sonnet / Haiku)
- Token counts, cache efficiency, top tools
- Estimated gross cost

## Requirements

- macOS
- Python 3.9+ (`brew install python` if needed)
- Claude Code installed and authenticated (`claude login`)


## Uninstall

```bash
claude-usage uninstall
```

## License

MIT
