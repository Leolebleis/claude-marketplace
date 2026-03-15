# claude-config

Personal Claude Code plugin marketplace (`Leolebleis/claude-config`).

## Structure

```
.claude-plugin/marketplace.json   # Plugin metadata + version
skills/<name>/SKILL.md            # One directory per skill
hooks/                            # SessionStart hooks (context injection)
md-hygiene.md                     # Session guidance (injected at session start via hook)
README.md                         # Public-facing install instructions
```

## Skills

| Skill | Purpose |
|-------|---------|
| french-writing | Auto-invoked for French text. Accents, contractions, tone. |
| precompact | Pre-compaction context preservation + Workflow Observer enrichment. |
| observer-setup | OTEL telemetry setup for new machines. |

## Hooks

The plugin injects session guidance at start via a `SessionStart` hook. This reminds Claude to suggest relevant skills at natural checkpoints (end of session, first time in a repo, before PRs, etc.). See `md-hygiene.md` for the full reference.

## Rules

- **Always increment the version** in `.claude-plugin/marketplace.json` when modifying skills or adding new ones. Use semver: patch for fixes, minor for new skills or features, major for breaking changes.
- **Never push directly to main.** Create a branch and open a PR.
- **Update README.md** when adding or removing skills.
