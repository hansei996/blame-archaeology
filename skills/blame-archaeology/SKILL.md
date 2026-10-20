---
name: blame-archaeology
description: Dig through git history before explaining why code looks the way it does. Use when the user asks why a line, function, or file is the way it is, when you are about to call something "legacy", "weird", "redundant", or "a bug", or before you propose deleting code whose purpose is not obvious.
license: MIT
---

# Blame archaeology

You do not get to explain why code looks like this until you have opened its history.

## Rules

1. **Pin the lines before you open your mouth.** State the exact range you are explaining: `path/to/file.ts:142-158`. No concrete range, no answer — ask which lines or pick the smallest enclosing function.
2. **Blame with whitespace and move detection on.** `git blame -w -C -C -L 142,158 -- path/to/file.ts`. `-w` skips whitespace-only churn, `-C -C` follows code moved across files. Plain `git blame` blames the reformatter, not the author.
3. **Walk the function, not just the line.** `git log -L :parseToken:src/auth.ts` follows a function through every edit. Use `git log -L 142,158:src/auth.ts` when the range is not a whole function.
4. **Follow renames.** `git log --follow --oneline -- src/auth.ts` and `git log --find-renames -M`. A file's history usually starts somewhere else.
5. **Read the commit, not the commit message.** `git show <sha> --stat` then `git show <sha>`. "fix bug" hides everything; the diff does not.
6. **Chase the linked issue or PR.** Extract `#N` from the message, then `gh pr view <N> --json title,body,comments` or `gh issue view <N>`. Cross-check with `gh pr list --search <sha> --state all` and `git log --grep='#<N>' --oneline`.
7. **When there is no link, say so with the commands you ran.** Fixed wording: `No linked issue or PR found (ran: gh pr list --search <sha>, git log --grep='#N'). Motive below is inferred from the diff only — confidence: low.` Never invent a ticket number.
8. **Label every claim with its evidence grade.** `[verbatim]` = quoted from commit/PR/issue. `[diff]` = read from the patch. `[guess]` = neither. A motive sentence with no grade is a guess; mark it.
9. **Blame is not authorship.** `git blame` names whoever last touched the line, which is often a rename, a lint pass, or a merge. Say "last touched by X" and keep looking for the original author with `git log -L`.
10. **Report the history; do not rewrite it.** Do not refactor, "modernise", or delete based on this report. If the history shows the code is load-bearing, say what breaks and stop.

## Output shape

```
来历:      <the series of commits that produced this shape, oldest first, one line each>
谁改的:    <sha (author, YYYY-MM-DD) — "last touched" vs "original author">
动机证据:  <verbatim quote + link, or "none found"> — evidence grade: [verbatim] / [diff] / [guess]
风险提示:  <what breaks if this changes; the caller, test, or invariant that depends on it>
不确定处:  <what you could not find + the exact commands you ran to look>
```

## Anti-patterns this skill exists to kill

- "This looks like leftover code from an old design — you can probably remove it."
- "The author probably wanted to avoid X here." (no commit cited)
- Explaining a design from the code alone, with `git log` never run.
- Reading only `git blame` and reporting the last formatter as the decision-maker.
