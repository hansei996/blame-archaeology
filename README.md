# blame-archaeology

> **It reads the git history before it explains the code.**

A skill for any coding agent. Kills design-intent guessing: no "why is this here?" answer gets written until the agent has run `git blame`, `git log -L`, and chased the linked issue or PR.

Works with Claude Code, Codex, Cursor, Gemini CLI, DeepSeek Harness — any agent that loads a `SKILL.md` / `AGENTS.md`.

## Install

Paste this into your agent:

```text
Install the blame-archaeology skill from https://github.com/hansei996/blame-archaeology — follow AGENTS.md.
```

Claude Code plugin style:

```bash
claude plugin marketplace add hansei996/blame-archaeology
claude plugin install blame-archaeology@blame-archaeology
```

Manual (always works — the marketplace command depends on your Claude Code version): copy `skills/blame-archaeology/SKILL.md` into your agent's skills directory.

## What it does

Replaces "this looks like legacy code, probably safe to remove" with a five-field report built from `git blame -w -C -C`, `git log -L :func:file`, `git log --follow`, `gh pr view`, and `gh issue view` — and marks every claim as quoted, read-from-diff, or guessed.

## Before / after

*(illustrative transcripts, reconstructed — not screen recordings)*

<table>
<tr><td width="50%">

**Before**

> This looks like leftover code from an earlier design. The retry loop with the 200ms floor is odd — probably someone was debugging a flaky network and forgot to remove it. I'd simplify it and let the normal backoff handle it.

</td><td width="50%">

**After**

> `来历` — three commits: `a1b2c3d` added the loop for the `credentials` path, `e4f5a6b` added the 200ms floor, `9c8d7e6` kept it while removing the other retry site.
> `谁改的` — `e4f5a6b` (dana, 2023-11-02) is the last touch on the floor; original loop by `a1b2c3d` (dana, 2023-08-14).
> `动机证据` — PR #418 "Windows CI: token endpoint returns SEC_E_NO_CREDENTIALS on first call": *"the first attempt after a cold boot fails instantly; sleep 200ms on attempt 0 only."* `[verbatim]`
> `风险提示` — `src/retry.ts:88` calls this on the cold-start path only; `test/retry.cold.spec.ts` asserts the floor. Removing it re-breaks #418.
> `不确定处` — no record of why 200ms specifically (ran `git log --grep='200ms'`, `gh pr list --search e4f5a6b`). `[guess]` it is a measured round-trip bound.

</td></tr>
</table>

## The rules

10 rules, full text in [SKILL.md](./skills/blame-archaeology/SKILL.md).

1. Pin the exact line range before answering.
2. Blame with `-w -C -C` so the formatter is not the author.
3. Walk the function with `git log -L :func:file`.
4. Follow renames with `git log --follow`.
5. Read the commit diff, not the commit message.
6. Chase the linked issue/PR with `gh`.
7. No link found? Say so, and name the commands you ran.
8. Every claim is tagged `[verbatim]` / `[diff]` / `[guess]`.
9. Blame names the last toucher, not the designer.
10. Report the history; do not rewrite it.

## Tune it

Fork it and edit `skills/blame-archaeology/SKILL.md`. Rule 8 is the one most people loosen (some agents over-tag and it gets noisy); rules 2 and 7 are the load-bearing ones — drop rule 2 and you get the reformatter's name as the decision-maker, drop rule 7 and the agent invents a ticket number to fill the gap.

## Why this exists

Agents are trained to be helpful, and helpfulness reads as "explain it now". Code has an author, a date, and usually a ticket; the cheapest wrong answer is the one that skips all three. This skill buys one `git log` before the first sentence of design intent.

## License

MIT
