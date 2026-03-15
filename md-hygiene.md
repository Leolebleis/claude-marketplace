# Session Guidance

Skills to suggest at natural checkpoints. Injected at session start via hook.

## Auto-Trigger Rules

| When | Suggest | Command |
|------|---------|---------|
| End of a productive session (new patterns, conventions, gotchas) | Capture learnings into CLAUDE.md | `/revise-claude-md` |
| First time in a repo, or CLAUDE.md feels stale | Audit and improve CLAUDE.md files | `/claude-md-improver` |
| After creating or modifying a skill | Quality-check the skill | `/skill-creator` |
| Setting up Claude Code in a new codebase | Recommend automations | `/claude-automation-recommender` |
| **Before creating a PR** | Review changed code for reuse, quality, and efficiency | `/simplify` |

## Never Auto-Invoke

- `/precompact` -- only run when the user explicitly requests it
