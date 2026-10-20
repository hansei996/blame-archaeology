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

*（示意对话，非录屏）*

| 之前 | 之后 |
|---|---|
| “这看着像早期设计留下的代码。那个 200ms 的重试下限很奇怪，大概是当时有人在调网络抖动，忘了删。我把它简化掉吧。” | “`来历` —— 三个 commit：`a1b2c3d` 为凭据路径加了重试循环，`e4f5a6b` 加了 200ms 下限。`谁改的` —— 下限是 dana 在 2023-11-02（`e4f5a6b`）最后改的。`动机证据` —— PR #418 原文：‘冷启动后第一次请求会立刻失败，只在 attempt 0 上睡 200ms。’`风险提示` —— `src/retry.ts:88` 只在冷启动路径调用它，`test/retry.cold.spec.ts` 断言了这个下限，删掉会重新触发 #418。`不确定处` —— 为什么正好是 200ms 没有记录（跑过 `git log --grep='200ms'`），标为猜测。” |

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
