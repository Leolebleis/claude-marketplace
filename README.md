# claude-config

Personal Claude Code plugin with shared skills.

## Install

```bash
claude plugin install Leolebleis/claude-config
```

## Skills

- **french-writing** -- Auto-invoked when writing French text. Accent rules, contractions, gaming terms, tone guidelines.
- **precompact** -- Pre-compaction context preservation. Run before compacting to persist valuable conversation context.
- **observer-setup** -- Set up OTEL telemetry export for Claude Code on a new machine.
- **pc-performance-audit** -- Audit a remote Windows PC via SSH for performance bottlenecks. Diagnoses CPU, RAM, GPU, storage, bloatware, and produces a ranked fix plan with apply/verify/rollback commands.

## Session Guidance (auto-injected)

At session start, the plugin injects guidance so Claude suggests the right skill at natural checkpoints:

- `/revise-claude-md` -- after productive sessions with new learnings
- `/claude-md-improver` -- when entering a repo or auditing CLAUDE.md quality
- `/skill-creator` -- after creating or modifying skills
- `/claude-automation-recommender` -- when setting up Claude Code for a new project
- `/simplify` -- before creating a PR (code reuse, quality, efficiency review)
