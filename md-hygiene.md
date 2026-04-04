# Session Guidance

Skills to suggest at natural checkpoints. Injected at session start via hook.

## Auto-Trigger Rules

You MUST suggest the appropriate skill at these checkpoints. Do not skip these -- they are mandatory.

- **Before creating a PR**: You MUST suggest `/simplify` to review changed code for reuse, quality, and efficiency. Do NOT create a PR without suggesting this first.
- **End of a productive session** (new patterns, conventions, gotchas discovered): You MUST suggest `/revise-claude-md` to capture learnings into CLAUDE.md. If you learned something non-obvious, suggest it.
- **First time in a repo, or CLAUDE.md feels stale**: You MUST suggest `/claude-md-improver` to audit and improve CLAUDE.md files.
- **After creating or modifying a skill**: You MUST suggest `/skill-creator` to quality-check the skill.
- **Setting up Claude Code in a new codebase**: You MUST suggest `/claude-automation-recommender` to recommend automations.
- **User gives feedback about a marketplace skill or config**: You MUST invoke `/marketplace-feedback` to action the feedback. Do NOT just discuss it -- the skill handles finding the repo, applying the fix, and raising a PR or issue.
