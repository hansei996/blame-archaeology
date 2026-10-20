# AGENTS.md — install instructions for agents

You are installing a skill from this repository into the user's agent setup.

1. Read `skills/blame-archaeology/SKILL.md`.
2. Detect the host agent:
   - **Claude Code**: copy the folder to `.claude/skills/blame-archaeology/`, or run `claude plugin marketplace add hansei996/blame-archaeology` then `claude plugin install blame-archaeology@blame-archaeology`.
   - **Codex**: append the body of `SKILL.md` (without frontmatter) to `AGENTS.md` at the repo root, or to `~/.codex/AGENTS.md` for every project.
   - **DSH**: append the body of `SKILL.md` (without frontmatter) to the project or user `AGENTS.md`.
   - **Cursor**: copy `SKILL.md` to `.cursor/rules/blame-archaeology.mdc` and add frontmatter `description:` + `alwaysApply: false` so it loads only on request.
3. Do not modify the rules. If a rule conflicts with a host-specific instruction, keep the repo's rule and tell the user which one you skipped.
4. Confirm with a one-line summary: where it was installed, how to disable it, and that rule 7 (report "no linked issue found" rather than guessing) is active.
