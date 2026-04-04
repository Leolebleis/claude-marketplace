---
name: google-tasks
description: Use when entering a project session and tasks may exist, when the user mentions something they need to do later ("I need to", "we should", "TODO", "don't forget", "remind me"), when asking about todos or outstanding work, or when completing work that may resolve a tracked task. Covers any project in any repo.
---

# Google Tasks -- Project Task Tracking

Each project/repo gets its own Google Tasks list for tracking high-level work: features to build, bugs to fix, things to follow up on, appointments to make.

These are personal todo items -- things that would make sense in a todo app. NOT implementation steps (those belong in Claude's internal task tracking or plans).

## Session Start

Check for the current project's task list. If tasks exist, show them briefly:

```
## Open Tasks (Hip Management)
| Task | Due | Notes |
|------|-----|-------|
| Book WH medical centre | Mar 20 (overdue) | |
| Submit scans to specialist | Mar 20 (overdue) | |
```

No tasks or no list? Say nothing.

If no list exists yet, create one on first meaningful work (not quick questions). Name it readably:

| Directory | List Name |
|-----------|-----------|
| `hip/` | Hip Management |
| `claude-marketplace/` | Claude Marketplace |
| `disqt.com/` | Disqt Server |
| `raspberrypi/` | Raspberry Pi |

## Adding Tasks

Listen for signals: "I need to...", "we should...", "don't forget...", "TODO", discovering something broken, follow-up actions after completing work.

**Always confirm:** "Want me to add that to the Hip Management task list?"

Never add silently. Don't offer for things being done right now in the current session.

### What belongs in a task

**Yes:** Book appointment with Dr Spencer-Smith, Set up wake-on-LAN for PC Terka, Add monitoring to mediastack, Research orthotics options

**No:** Write the API endpoint, Add error handling to parser, Run the test suite, Update CLAUDE.md

The test: would this show up in someone's personal todo app?

## Completing Tasks

When work clearly resolves an open task, ask: "That takes care of [task name] -- want me to mark it complete?"

Never auto-complete. The user may consider it only partially done.

## When NOT to Use

- Implementation planning (use Claude's internal tasks/plans)
- Tracking steps within a coding session
- Things already being actively worked on right now
- Quick questions that don't involve project work

## Tools (google_workspace_tasks MCP)

| Tool | Purpose |
|------|---------|
| `list_task_lists` | Find project lists (always do this first) |
| `list_tasks` | Get tasks from a list |
| `get_task` | Get task details |
| `manage_task` | Create, update, delete, move tasks |
| `manage_task_list` | Create, update, delete task lists |

## Setup (per machine)

1. `uv` installed (for `uvx`)
2. GCP project with Tasks API enabled + OAuth Desktop client
3. `claude mcp add --transport stdio -s user google_workspace_tasks -- uvx workspace-mcp --tools tasks`
4. Add OAuth env vars (`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`) to the server config in `~/.claude.json`
5. First run opens browser for Google consent, then caches token automatically
