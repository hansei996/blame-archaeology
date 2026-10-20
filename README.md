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

One full run on a real repository, including the case where the linked number resolves to nothing, is in **[examples/session-log.md](./examples/session-log.md)**.

## Before / after

Asked why `backoff_delay` looks the way it does, an agent that never opened the history still gives a confident answer:

> The `if attempt == 0` branch is redundant — the exponential ramp below already produces 50ms on the first attempt, which is ordinary backoff behaviour. Delete the branch and let the ramp cover attempt 0.

The same question answered by the rules. Pinned range: `src/auth/client.py:24-27`.

```python
def backoff_delay(attempt):
    if attempt == 0:
        # The credential provider is still initialising when the first attempt
        # runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
        return COLD_START_FLOOR_MS / 1000
    return (BACKOFF_BASE_MS * 2 ** attempt) / 1000
```

`git blame` with no flags names the newest commit in the file:

```console
$ git blame -L 24,27 -- src/auth/client.py
08dfe7ae (Dana Okonkwo 2024-03-13 14:52:00 +0800 24)     if attempt == 0:
08dfe7ae (Dana Okonkwo 2024-03-13 14:52:00 +0800 25)         # The credential provider is still initialising when the first attempt
08dfe7ae (Dana Okonkwo 2024-03-13 14:52:00 +0800 26)         # runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
08dfe7ae (Dana Okonkwo 2024-03-13 14:52:00 +0800 27)         return COLD_START_FLOOR_MS / 1000
```

`08dfe7a` is `Normalise indentation to spaces to match .editorconfig`. Those four lines were not designed there — they were re-indented there. Rule 2:

```console
$ git blame -w -C -C -L 24,27 -- src/auth/client.py
ce4d1e73 (Dana Okonkwo 2024-03-12 11:27:00 +0800 24)     if attempt == 0:
ce4d1e73 (Dana Okonkwo 2024-03-12 11:27:00 +0800 25)         # The credential provider is still initialising when the first attempt
ce4d1e73 (Dana Okonkwo 2024-03-12 11:27:00 +0800 26)         # runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
ce4d1e73 (Dana Okonkwo 2024-03-12 11:27:00 +0800 27)         return COLD_START_FLOOR_MS / 1000
```

Now the lines belong to `ce4d1e7`, the commit whose diff adds `COLD_START_FLOOR_MS = 200`, a comment naming the reason, and a test that pins the value. Its message ends in `(#1)`, so rule 6 applies — chase the number:

```console
$ git log --grep='#1' --oneline
ce4d1e7 Hold attempt 0 to a fixed 200ms floor on cold start (#1)
```

```console
$ gh pr list --search ce4d1e7 --state all
no git remotes found
```

`#1` resolves to nothing. Rule 7 has a fixed sentence for exactly this, instead of a guess:

> No linked issue or PR found (ran: gh pr list --search ce4d1e7, git log --grep='#1'). Motive below is inferred from the diff only — confidence: low.

The report:

```text
来历:      0dae26c  Add token client and session opener — fetch_token, no retry
           6e7bbad  Retry token fetches with exponential backoff — the loop plus backoff_delay(attempt)
           2cb4f4f  Move the token client into an auth package — src/client.py becomes src/auth/client.py, 0 lines changed
           ce4d1e7  Hold attempt 0 to a fixed 200ms floor on cold start (#1) — the attempt == 0 branch
           08dfe7a  Normalise indentation to spaces to match .editorconfig — whitespace only

谁改的:    ce4d1e73 (Dana Okonkwo, 2024-03-12) last touched the floor. The surrounding backoff_delay
           was written by 6e7bbad (Dana Okonkwo, 2024-03-05). Plain git blame answers 08dfe7ae
           (2024-03-13) for all four pinned lines — that is the reformat commit, not the author.
           Last touched, not original author.

动机证据: [verbatim] commit subject of ce4d1e7: "Hold attempt 0 to a fixed 200ms floor on cold start (#1)"
           [diff] the same commit ships the in-code comment: "The credential provider is still
           initialising when the first attempt runs, so attempt 0 needs a fixed floor instead of the
           50ms ramp."
           [guess] why 200 and not 100 or 150: nothing in the history says.

风险提示: src/tests/test_backoff.py:8 asserts backoff_delay(0) == 0.2 and that test passes today
           (section 8). Delete the attempt-0 branch and the suite fails; the first failure after a
           cold start would also sleep 50ms instead of 200ms, because src/auth/client.py:19 sleeps
           backoff_delay(attempt) on every failed attempt. [diff]

不确定处: No linked issue or PR found (ran: gh pr list --search ce4d1e7, git log --grep='#1'). Motive below is inferred from the diff only — confidence: low.
           Both gh calls returned "no git remotes found": this repository has no GitHub remote, so
           no PR or issue could be checked even if one existed. Commands run are listed in section 7.
```

Full transcript — `git log -L :backoff_delay:`, `git log --follow`, `git show ce4d1e7`, the whole file blamed both ways, and the test run: **[examples/session-log.md](./examples/session-log.md)**.

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
