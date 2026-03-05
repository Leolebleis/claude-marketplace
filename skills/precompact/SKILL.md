---
name: precompact
description: "Pre-Compaction Context Preservation. Use when about to compact, or when the user says /precompact. Persists valuable conversation context before lossy compaction."
---

# Pre-Compaction Context Preservation

Run this before compacting to persist valuable conversation context. Compaction is lossy -- this is your only chance to save context.

## What Auto Memory Already Handles

Claude's Auto Memory automatically updates `MEMORY.md` with learned patterns, gotchas, and preferences. **Do not duplicate this work.** Focus on what Auto Memory does NOT handle: docs, skills, and in-progress work.

## Documentation Hierarchy

When saving context, put information in the RIGHT place. This prevents hot-context bloat and duplication.

```
HOT (loaded every session -- keep lean):
  MEMORY.md              ~40 lines max. Cross-cutting patterns, preferences, shell gotchas only.
                          NO project-specific details. Points to docs/ for details.
  ~/.claude/CLAUDE.md     OS-agnostic user preferences only.
  CLAUDE.md (root)        Slim project index. No inline details.

ON-DEMAND (loaded when working on the relevant project):
  <project>/CLAUDE.md          Project ops: deploy, build, config, project table.
  <project>/docs/*.md          Detailed infrastructure/design docs. One per topic.

SKILLS (loaded when invoked):
  ~/.claude/commands/                Global workflows (this file, etc).
  <project>/.claude/commands/        Project-specific commands.
```

### What goes where (decision tree)

1. **Is it about a specific project's infrastructure?** -> `<project>/docs/<topic>.md`
2. **Is it about a project's ops (deploy, networking)?** -> `<project>/CLAUDE.md`
3. **Is it a cross-cutting pattern (affects multiple projects)?** -> `MEMORY.md`
4. **Is it a reusable workflow or ops procedure?** -> A skill file (global or project-level)
5. **Is it in-progress work?** -> `<project>/docs/in-progress-<topic>.md`
6. **Is it a design doc?** -> `docs/plans/YYYY-MM-DD-<topic>-design.md`

### Anti-patterns to avoid

- **Don't put project-specific details in MEMORY.md** -- they belong in `<project>/docs/`
- **Don't duplicate credentials across files** -- each project's docs have the canonical credentials
- **Don't put project-specific info in `~/.claude/CLAUDE.md`** -- it must stay OS-agnostic
- **Don't let MEMORY.md grow past ~50 lines** -- if it's getting long, content belongs in project docs

## Procedure

### 1. Audit the conversation

Scan for:
- **New reference knowledge**: Server paths, config details, deployment procedures, architecture decisions
- **New workflows**: Reusable procedures that should become skills
- **In-progress work**: Unfinished tasks, next steps, blockers

### 2. Update project docs/ files (if applicable)

If the conversation revealed new infrastructure knowledge, config, or deployment details:

- Identify which project it belongs to
- Check `<project>/CLAUDE.md` for the docs index -- find the right `<project>/docs/*.md` file
- Read the target file, add/update relevant sections
- If a new topic emerged, create a new `<project>/docs/*.md` and add it to the project's CLAUDE.md index
- Keep entries factual and concise

### 3. Update project CLAUDE.md index (if applicable)

If new projects or docs were added:
- Add entries to the project table or docs index
- Keep each CLAUDE.md as a slim directory -- no inline details

### 4. Create or update skills (if applicable)

If a new reusable workflow was established:
- **Global skills**: `~/.claude/commands/<name>.md`
- **Project skills**: `<project>/.claude/commands/<name>.md`

### 5. Document in-progress work (if applicable)

If there's unfinished work that a future session needs to continue:
- Write a state file: `<project>/docs/in-progress-<topic>.md`
- `<topic>` must describe the work, not the date
- Do NOT use `in-progress-YYYY-MM-DD.md` -- a date tells you nothing about the content
- Include: what was done, what remains, key decisions, blockers

### 6. Report what was saved

Tell the user which files were updated/created and summarize what was persisted.

## 7. Workflow Observer Enrichment (if applicable)

If you used custom skills this session and `OTEL_EXPORTER_OTLP_ENDPOINT` is set, self-assess and POST to the Workflow Observer.

1. Reflect: Did you accomplish the goals? How many times were you blocked or corrected?
2. Extract the observer host from `OTEL_EXPORTER_OTLP_ENDPOINT` (same host, port 3500)
3. Run this Bash command with your assessment (adjust values):

```bash
curl -s -X POST http://<OBSERVER_HOST>:3500/observer/api/enrich \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"<your session ID>","skill":"<primary skill used>","confidence":<0.0-1.0>,"blockers_hit":<int>,"user_corrections":<int>,"goal_completion":"<full|partial|failed>","notes":"<one sentence>"}'
```

Keep this lightweight -- one curl call, ~50 tokens of reasoning. Skip if the observer is unreachable.

## Guidelines

- **Be aggressive about saving** -- better to save something redundant than lose something valuable
- **Don't touch MEMORY.md** -- Auto Memory handles it
- **Prefer updating over appending** -- update existing entries rather than adding duplicates
- **Verify before writing** -- always read the target file before editing
