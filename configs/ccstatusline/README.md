# ccstatusline config

Backup of the [ccstatusline](https://www.npmjs.com/package/ccstatusline) status bar configuration.

## Location

Config lives at `~/.config/ccstatusline/settings.json`. To restore, copy `settings.json` from this directory there.

## Claude Code integration

In `~/.claude/settings.json`:

```json
"statusLine": {
  "type": "command",
  "command": "bunx -y ccstatusline@latest",
  "padding": 0
}
```

Two hooks are auto-managed by ccstatusline (tagged `_tag: "ccstatusline-managed"`):

- **PreToolUse** (matcher: `Skill`) -- tracks active skills
- **UserPromptSubmit** -- updates status on each prompt

## Layout

Three lines, powerline-styled with Nord Aurora theme:

| Line | Segments |
|------|----------|
| 1 | Token speed (120s window), session usage progress bar, reset timer |
| 2 | Git root dir, branch, changes, working directory (last 2 segments) |
| 3 | Hostname, context length, active skills (up to 5) |

Flex mode: `full-until-compact` (collapses at 60 char threshold).
