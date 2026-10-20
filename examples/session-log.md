# Session log — one pinned range, five commits, real terminal output

Every command below was run, in this order, from the root of a repository built by
[`rebuild-demo.ps1`](./rebuild-demo.ps1):

```console
$ pwsh -File examples/rebuild-demo.ps1 -Target C:\tmp\demo-repo
```

That script writes the files and makes the five commits with a fixed author identity and fixed
timestamps, so the commit ids quoted here are the ids you get when you rebuild it. It was rebuilt
twice into separate directories and produced the same five ids both times.

The question: `backoff_delay` special-cases `attempt == 0` with a fixed 200ms sleep and then falls
through to a ramp that already covers attempt 0. Is the branch dead weight?

## 1. The history, oldest first

```console
$ git log --oneline --graph --find-renames
* 08dfe7a Normalise indentation to spaces to match .editorconfig
* ce4d1e7 Hold attempt 0 to a fixed 200ms floor on cold start (#1)
* 2cb4f4f Move the token client into an auth package
* 6e7bbad Retry token fetches with exponential backoff
* 0dae26c Add token client and session opener
```

Five commits, so the whole history fits on one screen — which is the point of running it: the answer
is in there, and none of it is visible in the code.

## 2. Pin the range (rule 1)

Pinned range: `src/auth/client.py:24-27`.

```python
def backoff_delay(attempt):
    if attempt == 0:
        # The credential provider is still initialising when the first attempt
        # runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
        return COLD_START_FLOOR_MS / 1000
    return (BACKOFF_BASE_MS * 2 ** attempt) / 1000
```

## 3. Blame with the reformatter switched off (rule 2)

Plain `git blame` first, because that is where most explanations stop:

```console
$ git blame -L 24,27 -- src/auth/client.py
08dfe7ae (Dana Okonkwo 2024-03-13 14:52:00 +0800 24)     if attempt == 0:
08dfe7ae (Dana Okonkwo 2024-03-13 14:52:00 +0800 25)         # The credential provider is still initialising when the first attempt
08dfe7ae (Dana Okonkwo 2024-03-13 14:52:00 +0800 26)         # runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
08dfe7ae (Dana Okonkwo 2024-03-13 14:52:00 +0800 27)         return COLD_START_FLOOR_MS / 1000
```

All four lines belong to `08dfe7a`, the newest commit in the repository. The same range with
whitespace and move detection on:

```console
$ git blame -w -C -C -L 24,27 -- src/auth/client.py
ce4d1e73 (Dana Okonkwo 2024-03-12 11:27:00 +0800 24)     if attempt == 0:
ce4d1e73 (Dana Okonkwo 2024-03-12 11:27:00 +0800 25)         # The credential provider is still initialising when the first attempt
ce4d1e73 (Dana Okonkwo 2024-03-12 11:27:00 +0800 26)         # runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
ce4d1e73 (Dana Okonkwo 2024-03-12 11:27:00 +0800 27)         return COLD_START_FLOOR_MS / 1000
```

Same four lines, different commit: `ce4d1e7`, one day earlier. `08dfe7a` is the indentation commit —
it rewrote indented lines from tabs to spaces and changed no code. Plain blame credits it with 15 of
the 28 lines in the file; with `-w` it credits it with none (section 10 has the whole file both ways).
On this repository the two answers differ by one commit and one day. On a repository with a
four-year-old lint pass they differ by four years, and the lint pass is what gets named.

## 4. Walk the function across every edit (rule 3)

```console
$ git log -L :backoff_delay:src/auth/client.py
commit 08dfe7aec995fdf7cc8708e33a51dfcc1c25cf3b
Author: Dana Okonkwo <dana@blame-archaeology.invalid>
Date:   Wed Mar 13 14:52:00 2024 +0800

    Normalise indentation to spaces to match .editorconfig

diff --git a/src/auth/client.py b/src/auth/client.py
--- a/src/auth/client.py
+++ b/src/auth/client.py
@@ -23,6 +23,6 @@
 def backoff_delay(attempt):
-	if attempt == 0:
-		# The credential provider is still initialising when the first attempt
-		# runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
-		return COLD_START_FLOOR_MS / 1000
-	return (BACKOFF_BASE_MS * 2 ** attempt) / 1000
+    if attempt == 0:
+        # The credential provider is still initialising when the first attempt
+        # runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
+        return COLD_START_FLOOR_MS / 1000
+    return (BACKOFF_BASE_MS * 2 ** attempt) / 1000

commit ce4d1e73d576a3b440a8791a00935afa803d3a4e
Author: Dana Okonkwo <dana@blame-archaeology.invalid>
Date:   Tue Mar 12 11:27:00 2024 +0800

    Hold attempt 0 to a fixed 200ms floor on cold start (#1)

diff --git a/src/auth/client.py b/src/auth/client.py
--- a/src/auth/client.py
+++ b/src/auth/client.py
@@ -22,2 +23,6 @@
 def backoff_delay(attempt):
+	if attempt == 0:
+		# The credential provider is still initialising when the first attempt
+		# runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
+		return COLD_START_FLOOR_MS / 1000
 	return (BACKOFF_BASE_MS * 2 ** attempt) / 1000

commit 6e7bbad5f577a0349d330ae55e14a8d91c7f5b9f
Author: Dana Okonkwo <dana@blame-archaeology.invalid>
Date:   Tue Mar 5 16:40:00 2024 +0800

    Retry token fetches with exponential backoff

diff --git a/src/client.py b/src/client.py
--- a/src/client.py
+++ b/src/client.py
@@ -7,4 +22,2 @@
-def fetch_token(endpoint=DEFAULT_ENDPOINT, timeout=5):
-	request = urllib.request.Request(endpoint, method="POST")
-	with urllib.request.urlopen(request, timeout=timeout) as response:
-		return json.loads(response.read())["access_token"]
+def backoff_delay(attempt):
+	return (BACKOFF_BASE_MS * 2 ** attempt) / 1000

commit 0dae26cf52bf52b676e50d51bd9685061e0a6cba
Author: Dana Okonkwo <dana@blame-archaeology.invalid>
Date:   Mon Mar 4 10:12:00 2024 +0800

    Add token client and session opener

diff --git a/src/client.py b/src/client.py
--- /dev/null
+++ b/src/client.py
@@ -0,0 +7,4 @@
+def fetch_token(endpoint=DEFAULT_ENDPOINT, timeout=5):
+	request = urllib.request.Request(endpoint, method="POST")
+	with urllib.request.urlopen(request, timeout=timeout) as response:
+		return json.loads(response.read())["access_token"]
```

More than blame can tell you: `backoff_delay` did not exist before `6e7bbad`, which added it in the
same commit as the retry loop, and the oldest hunks are against `src/client.py`, not `src/auth/`.

## 5. Follow the rename (rule 4)

```console
$ git log --follow --oneline -- src/auth/client.py
08dfe7a Normalise indentation to spaces to match .editorconfig
ce4d1e7 Hold attempt 0 to a fixed 200ms floor on cold start (#1)
2cb4f4f Move the token client into an auth package
6e7bbad Retry token fetches with exponential backoff
0dae26c Add token client and session opener
```

```console
$ git show 2cb4f4f --stat
commit 2cb4f4f972639c1aaca3e93858816449a4196e17
Author: Dana Okonkwo <dana@blame-archaeology.invalid>
Date:   Wed Mar 6 09:05:00 2024 +0800

    Move the token client into an auth package

 src/auth/__init__.py     | 0
 src/{ => auth}/client.py | 0
 src/session.py           | 4 ++--
 3 files changed, 2 insertions(+), 2 deletions(-)
```

`src/{ => auth}/client.py | 0` — the file moved and not one line changed. A history search anchored
only at the current path would have started at `2cb4f4f` and found nothing older.

## 6. Read the commit, not the commit message (rule 5)

```console
$ git show ce4d1e7 --stat
commit ce4d1e73d576a3b440a8791a00935afa803d3a4e
Author: Dana Okonkwo <dana@blame-archaeology.invalid>
Date:   Tue Mar 12 11:27:00 2024 +0800

    Hold attempt 0 to a fixed 200ms floor on cold start (#1)

 src/auth/client.py        |  5 +++++
 src/tests/test_backoff.py | 16 ++++++++++++++++
 2 files changed, 21 insertions(+)
```

The stat line is already an argument: the commit that added the "redundant" floor also added a test
file. Now the patch:

```console
$ git show ce4d1e7
commit ce4d1e73d576a3b440a8791a00935afa803d3a4e
Author: Dana Okonkwo <dana@blame-archaeology.invalid>
Date:   Tue Mar 12 11:27:00 2024 +0800

    Hold attempt 0 to a fixed 200ms floor on cold start (#1)

diff --git a/src/auth/client.py b/src/auth/client.py
index e99cd9f..842acf6 100644
--- a/src/auth/client.py
+++ b/src/auth/client.py
@@ -4,6 +4,7 @@ import urllib.request
 
 DEFAULT_ENDPOINT = "https://auth.internal/token"
 BACKOFF_BASE_MS = 50
+COLD_START_FLOOR_MS = 200
 
 
 def fetch_token(endpoint=DEFAULT_ENDPOINT, timeout=5, attempts=3):
@@ -20,4 +21,8 @@ def fetch_token(endpoint=DEFAULT_ENDPOINT, timeout=5, attempts=3):
 
 
 def backoff_delay(attempt):
+	if attempt == 0:
+		# The credential provider is still initialising when the first attempt
+		# runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
+		return COLD_START_FLOOR_MS / 1000
 	return (BACKOFF_BASE_MS * 2 ** attempt) / 1000
diff --git a/src/tests/test_backoff.py b/src/tests/test_backoff.py
new file mode 100644
index 0000000..2696114
--- /dev/null
+++ b/src/tests/test_backoff.py
@@ -0,0 +1,16 @@
+import unittest
+
+from auth import client
+
+
+class BackoffTest(unittest.TestCase):
+	def test_first_attempt_waits_the_cold_start_floor(self):
+		self.assertEqual(client.backoff_delay(0), 0.2)
+
+	def test_later_attempts_follow_the_ramp(self):
+		self.assertEqual(client.backoff_delay(1), 0.1)
+		self.assertEqual(client.backoff_delay(3), 0.4)
+
+
+if __name__ == "__main__":
+	unittest.main()
```

Three things the code alone cannot tell you: the floor arrived as a named constant
`COLD_START_FLOOR_MS = 200`, it arrived with a comment naming the reason (the credential provider is
still initialising on the first attempt), and it arrived with two tests, one of which asserts the
floor exactly.

## 7. Chase the linked number (rule 6), and what to say when it resolves to nothing (rule 7)

The subject ends in `(#1)`. Extract it and search:

```console
$ git log --grep='#1' --oneline
ce4d1e7 Hold attempt 0 to a fixed 200ms floor on cold start (#1)
```

The grep finds the commit that wrote the number, and nothing else. Ask GitHub about it:

```console
$ gh pr list --search ce4d1e7 --state all
no git remotes found
```

```console
$ gh issue view 1
no git remotes found
```

`#1` points at nothing. This is the case rule 7 exists for: the honest output is the fixed sentence
plus the commands that were actually run, never an invented ticket number.

> No linked issue or PR found (ran: gh pr list --search ce4d1e7, git log --grep='#1'). Motive below is inferred from the diff only — confidence: low.

## 8. Is the branch load-bearing? (rule 10)

The commit added a test that asserts the floor, so run it instead of trusting the diff:

```console
$ python -m unittest discover -s tests -v
test_first_attempt_waits_the_cold_start_floor (test_backoff.BackoffTest.test_first_attempt_waits_the_cold_start_floor) ... ok
test_later_attempts_follow_the_ramp (test_backoff.BackoffTest.test_later_attempts_follow_the_ramp) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.000s

OK
```

`test_first_attempt_waits_the_cold_start_floor` passes, and it passes because of the branch under
question: `backoff_delay(0)` is 0.2 only because of `COLD_START_FLOOR_MS`. Delete the branch and the
suite fails. That is the answer to "is it redundant" — no, and the cost of finding out is one command.

## 9. The report

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

## 10. Appendix: the whole file, blamed both ways

Section 3 claims the reformat commit owns 15 of 28 lines under plain blame and none under `-w`. The
same two commands over the entire file instead of one range:

```console
$ git blame -s src/auth/client.py
^0dae26c src/client.py       1) import json
6e7bbad5 src/client.py       2) import time
^0dae26c src/client.py       3) import urllib.request
^0dae26c src/client.py       4) 
^0dae26c src/client.py       5) DEFAULT_ENDPOINT = "https://auth.internal/token"
6e7bbad5 src/client.py       6) BACKOFF_BASE_MS = 50
ce4d1e73 src/auth/client.py  7) COLD_START_FLOOR_MS = 200
^0dae26c src/client.py       8) 
^0dae26c src/client.py       9) 
6e7bbad5 src/client.py      10) def fetch_token(endpoint=DEFAULT_ENDPOINT, timeout=5, attempts=3):
08dfe7ae src/auth/client.py 11)     last_error = None
08dfe7ae src/auth/client.py 12)     for attempt in range(attempts):
08dfe7ae src/auth/client.py 13)         try:
08dfe7ae src/auth/client.py 14)             request = urllib.request.Request(endpoint, method="POST")
08dfe7ae src/auth/client.py 15)             with urllib.request.urlopen(request, timeout=timeout) as response:
08dfe7ae src/auth/client.py 16)                 return json.loads(response.read())["access_token"]
08dfe7ae src/auth/client.py 17)         except OSError as error:
08dfe7ae src/auth/client.py 18)             last_error = error
08dfe7ae src/auth/client.py 19)             time.sleep(backoff_delay(attempt))
08dfe7ae src/auth/client.py 20)     raise last_error
6e7bbad5 src/client.py      21) 
6e7bbad5 src/client.py      22) 
6e7bbad5 src/client.py      23) def backoff_delay(attempt):
08dfe7ae src/auth/client.py 24)     if attempt == 0:
08dfe7ae src/auth/client.py 25)         # The credential provider is still initialising when the first attempt
08dfe7ae src/auth/client.py 26)         # runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
08dfe7ae src/auth/client.py 27)         return COLD_START_FLOOR_MS / 1000
08dfe7ae src/auth/client.py 28)     return (BACKOFF_BASE_MS * 2 ** attempt) / 1000
```

```console
$ git blame -w -C -C -s src/auth/client.py
^0dae26c src/client.py       1) import json
6e7bbad5 src/client.py       2) import time
^0dae26c src/client.py       3) import urllib.request
^0dae26c src/client.py       4) 
^0dae26c src/client.py       5) DEFAULT_ENDPOINT = "https://auth.internal/token"
6e7bbad5 src/client.py       6) BACKOFF_BASE_MS = 50
ce4d1e73 src/auth/client.py  7) COLD_START_FLOOR_MS = 200
^0dae26c src/client.py       8) 
^0dae26c src/client.py       9) 
6e7bbad5 src/client.py      10) def fetch_token(endpoint=DEFAULT_ENDPOINT, timeout=5, attempts=3):
6e7bbad5 src/client.py      11)     last_error = None
6e7bbad5 src/client.py      12)     for attempt in range(attempts):
6e7bbad5 src/client.py      13)         try:
^0dae26c src/client.py      14)             request = urllib.request.Request(endpoint, method="POST")
^0dae26c src/client.py      15)             with urllib.request.urlopen(request, timeout=timeout) as response:
^0dae26c src/client.py      16)                 return json.loads(response.read())["access_token"]
6e7bbad5 src/client.py      17)         except OSError as error:
6e7bbad5 src/client.py      18)             last_error = error
6e7bbad5 src/client.py      19)             time.sleep(backoff_delay(attempt))
6e7bbad5 src/client.py      20)     raise last_error
6e7bbad5 src/client.py      21) 
6e7bbad5 src/client.py      22) 
6e7bbad5 src/client.py      23) def backoff_delay(attempt):
ce4d1e73 src/auth/client.py 24)     if attempt == 0:
ce4d1e73 src/auth/client.py 25)         # The credential provider is still initialising when the first attempt
ce4d1e73 src/auth/client.py 26)         # runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.
ce4d1e73 src/auth/client.py 27)         return COLD_START_FLOOR_MS / 1000
6e7bbad5 src/client.py      28)     return (BACKOFF_BASE_MS * 2 ** attempt) / 1000
```

Two more details fall out of the second listing. `08dfe7ae` disappears from the file entirely. And
`-C -C` walks lines 14-16 — the `Request` / `urlopen` / `return` trio — back past the retry commit to
`0dae26c` itself, because that code was only moved and re-indented, never rewritten.
