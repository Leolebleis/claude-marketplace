# claude-marketplace

Personal Claude Code skills (`Leolebleis/claude-marketplace`).

## Structure

```
.claude-plugin/marketplace.json   # Plugin metadata + version
skills/<name>/SKILL.md            # One directory per skill
README.md                         # Public-facing install instructions
```

## Skills

| Skill | Purpose |
|-------|---------|
| french-writing | Auto-invoked for French text. Accents, contractions, tone. |
| google-tasks | Manage Google Tasks -- list, create, complete, update, search. |
| pc-performance-audit | Remote Windows PC performance audit via SSH. System-level: services, RAM/CPU/disk, bloatware, OS state, ASUS Armoury Crate, HVCI/HAGS. |
| game-tuning | Per-game optimization: G-Sync 101 stack, DLSS/Frame Gen, Reflex, per-app NVCP profiles, launch options, in-game settings. CS2 cookbook in references/. |
| solved-problem | Prior-art research before building custom. Parallel subagents across GitHub/Reddit/HN/awesome-lists/blogs, ranked tools with pros/cons, recommendation. |

## MCP Servers (configured locally per machine, not in plugin)

| Server | Purpose |
|--------|---------|
| google_workspace_tasks | Google Tasks via `workspace-mcp` (taylorwilsdon/google_workspace_mcp). Config in `~/.claude/settings.json` with OAuth creds. |

## Rules

- **Always increment the version** in `.claude-plugin/marketplace.json` when modifying skills or adding new ones. Use semver: patch for fixes, minor for new skills or features, major for breaking changes.
- **Never push directly to main.** Create a branch and open a PR.
- **Update README.md** when adding or removing skills.
