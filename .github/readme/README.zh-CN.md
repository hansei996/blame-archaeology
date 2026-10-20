# blame-archaeology

> **先读 git 历史，再解释代码。**

给任意 coding agent 用的技能。专治“瞎猜设计意图”：在它跑过 `git blame`、`git log -L`、追过关联的 issue / PR 之前，任何“这段代码为什么长这样”的回答都不许写出来。

适用于 Claude Code、Codex、Cursor、Gemini CLI、DeepSeek Harness —— 只要能加载 `SKILL.md` / `AGENTS.md`。

## 安装

把下面这句话粘给你的 agent：

```text
从 https://github.com/hansei996/blame-archaeology 安装 blame-archaeology 技能，按 AGENTS.md 的说明做。
```

## 它做什么

把“这像是历史遗留代码，应该可以删”换成一份五段式报告：用 `git blame -w -C -C`、`git log -L :func:file`、`git log --follow`、`gh pr view`、`gh issue view` 拿到证据，并且给每条结论标上「原文 / diff 推断 / 猜测」。

## 前后对比

问题：`backoff_delay` 给 `attempt == 0` 单独设了固定 200ms，然后再落到一条本来就能覆盖 attempt 0 的指数退避上。这个分支是不是该删？

钉住的行区间：`src/auth/client.py:24-27`。

```python
def backoff_delay(attempt):
    if attempt == 0:
        # The credential provider is still initialising when the first attempt
        # runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
        return COLD_START_FLOOR_MS / 1000
    return (BACKOFF_BASE_MS * 2 ** attempt) / 1000
```

| 之前 | 之后 |
|---|---|
| “这看着像早期设计留下的代码。那个 200ms 的重试下限很奇怪，大概是当时有人在调网络抖动，忘了删。我把它简化掉吧。” | “`来历` —— 五个 commit：`0dae26c` 加了 `fetch_token`；`6e7bbad` 加了重试循环和 `backoff_delay`；`2cb4f4f` 把文件挪进 `src/auth/`（0 行改动）；`ce4d1e7` 加了 attempt 0 的固定下限；`08dfe7a` 只把 tab 换成空格。`谁改的` —— 下限是 `ce4d1e7`（2024-03-12）写的，但裸 `git blame` 会回答 `08dfe7a`（2024-03-13）——那是重排提交，不是作者。`动机证据` —— `[verbatim]` `ce4d1e7` 的标题原文：`Hold attempt 0 to a fixed 200ms floor on cold start (#1)`；`[diff]` 同一个 commit 附带的注释写明凭据提供者在第一次尝试时还没初始化完，所以 attempt 0 要的是固定下限而不是 50ms 斜坡；为什么正好是 200ms，`[guess]`，历史里没有记录。`风险提示` —— `src/tests/test_backoff.py:8` 断言 `backoff_delay(0) == 0.2`，删掉这个分支测试立刻红；`src/auth/client.py:19` 每次失败都睡 `backoff_delay(attempt)`，冷启动首次失败会从 200ms 掉回 50ms。`不确定处` —— 没有关联的 issue 或 PR（固定句式见下），`#1` 指向空处。” |

同一段区间，两条命令，两个答案。裸 `git blame`（多数解释就停在这一步）：

```console
$ git blame -L 24,27 -- src/auth/client.py
08dfe7ae (Dana Okonkwo 2024-03-13 14:52:00 +0800 24)     if attempt == 0:
08dfe7ae (Dana Okonkwo 2024-03-13 14:52:00 +0800 25)         # The credential provider is still initialising when the first attempt
08dfe7ae (Dana Okonkwo 2024-03-13 14:52:00 +0800 26)         # runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
08dfe7ae (Dana Okonkwo 2024-03-13 14:52:00 +0800 27)         return COLD_START_FLOOR_MS / 1000
```

这四行全部记在 `08dfe7a` 名下——而 `08dfe7a` 就是那条只把 tab 改成空格的提交。加上 `-w -C -C`：

```console
$ git blame -w -C -C -L 24,27 -- src/auth/client.py
ce4d1e73 (Dana Okonkwo 2024-03-12 11:27:00 +0800 24)     if attempt == 0:
ce4d1e73 (Dana Okonkwo 2024-03-12 11:27:00 +0800 25)         # The credential provider is still initialising when the first attempt
ce4d1e73 (Dana Okonkwo 2024-03-12 11:27:00 +0800 26)         # runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
ce4d1e73 (Dana Okonkwo 2024-03-12 11:27:00 +0800 27)         return COLD_START_FLOOR_MS / 1000
```

同样的四行，换了个 commit：`ce4d1e7`，早一天。裸 blame 把整个文件 28 行里的 15 行都算在重排提交头上，`-w` 之后是 0 行（两种模式的完整输出见 [session-log 第 10 节](../../examples/session-log.md)）。一次格式重排就能把作者藏起来；如果仓库里有一次四年前的 lint 批量重排，裸 blame 报出来的就是那次 lint。

那 `#1` 是什么？查过之后，规则 7 的固定句式是：

> No linked issue or PR found (ran: gh pr list --search ce4d1e7, git log --grep='#1'). Motive below is inferred from the diff only — confidence: low.

全部命令、原始终端输出（含 `git log -L :backoff_delay:`、`git log --follow`、`git show ce4d1e7` 与断言测试的实跑结果）：[examples/session-log.md](../../examples/session-log.md)；重建这份历史的脚本：[examples/rebuild-demo.ps1](../../examples/rebuild-demo.ps1)。

## 十条规则

见 [SKILL.md](../../skills/blame-archaeology/SKILL.md)。

1. 先钉住具体行区间，再开口。
2. blame 必须带 `-w -C -C`，否则作者是格式化工具。
3. 用 `git log -L :func:file` 跟整个函数，而不是单行。
4. 用 `git log --follow` 追改名。
5. 读 commit 的 diff，不读 commit message。
6. 用 `gh` 追关联的 issue / PR。
7. 查不到就说查不到，并列出跑过的命令。
8. 每条结论标 `[verbatim]` / `[diff]` / `[guess]`。
9. blame 给的是"最后碰这行的人"，不是设计者。
10. 只报告历史，不顺手改代码。

第 2、7 条是承重的：去掉第 2 条，你会把格式化工具当成决策者；去掉第 7 条，agent 会为了填满「动机证据」那一栏编一个 issue 号。

## License

MIT
