<#
  Rebuild the five-commit demo repository whose history is recorded in
  examples/session-log.md.

  Usage:  pwsh -File examples/rebuild-demo.ps1 -Target C:\tmp\demo-repo

  Author identity and every commit timestamp are fixed, so the commit ids this
  script prints are the ids session-log.md quotes.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Target
)

$ErrorActionPreference = "Stop"
$LF = [string][char]10
$TAB = [string][char]9

function As-Text([string[]]$Lines) { ($Lines -join $LF) + $LF }

function Write-RepoFile([string]$Path, [string]$Text) {
    $dir = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    [IO.File]::WriteAllBytes($Path, [Text.Encoding]::UTF8.GetBytes($Text))
}

function ConvertTo-Tabs([string]$Text) {
    $converted = foreach ($line in ($Text -split $LF)) {
        if ($line -match "^( +)") {
            $depth = [int]($matches[1].Length / 4)
            ($TAB * $depth) + $line.Substring($matches[1].Length)
        }
        else { $line }
    }
    $converted -join $LF
}

function Invoke-Commit([string]$Message, [string]$When) {
    $env:GIT_AUTHOR_DATE = $When
    $env:GIT_COMMITTER_DATE = $When
    git -C $Target add -A
    if ($LASTEXITCODE -ne 0) { throw "git add failed" }
    git -C $Target commit -q -m $Message
    if ($LASTEXITCODE -ne 0) { throw "git commit failed" }
    git -C $Target log --oneline -1
}

if (Test-Path -LiteralPath (Join-Path $Target ".git")) { throw "target already holds a git repository: $Target" }
if (-not (Test-Path -LiteralPath $Target)) { New-Item -ItemType Directory -Force -Path $Target | Out-Null }

$env:GIT_AUTHOR_NAME = "Dana Okonkwo"
$env:GIT_AUTHOR_EMAIL = "dana@blame-archaeology.invalid"
$env:GIT_COMMITTER_NAME = "Dana Okonkwo"
$env:GIT_COMMITTER_EMAIL = "dana@blame-archaeology.invalid"

git -C $Target init -q -b main
git -C $Target config core.autocrlf false
git -C $Target config user.name "Dana Okonkwo"
git -C $Target config user.email "dana@blame-archaeology.invalid"

# --- file bodies as they read at HEAD (4-space indent) ----------------------

$gitignore = As-Text @('__pycache__/', '*.pyc')

$client1 = As-Text @(
'import json',
'import urllib.request',
'',
'DEFAULT_ENDPOINT = "https://auth.internal/token"',
'',
'',
'def fetch_token(endpoint=DEFAULT_ENDPOINT, timeout=5):',
'    request = urllib.request.Request(endpoint, method="POST")',
'    with urllib.request.urlopen(request, timeout=timeout) as response:',
'        return json.loads(response.read())["access_token"]'
)

$session1 = As-Text @('import client', '', 'SESSION_TTL_SECONDS = 3600', '', '', 'def open_session():',
'    token = client.fetch_token()',
'    return {"token": token, "ttl": SESSION_TTL_SECONDS}'
)

$client2 = As-Text @(
'import json',
'import time',
'import urllib.request',
'',
'DEFAULT_ENDPOINT = "https://auth.internal/token"',
'BACKOFF_BASE_MS = 50',
'',
'',
'def fetch_token(endpoint=DEFAULT_ENDPOINT, timeout=5, attempts=3):',
'    last_error = None',
'    for attempt in range(attempts):',
'        try:',
'            request = urllib.request.Request(endpoint, method="POST")',
'            with urllib.request.urlopen(request, timeout=timeout) as response:',
'                return json.loads(response.read())["access_token"]',
'        except OSError as error:',
'            last_error = error',
'            time.sleep(backoff_delay(attempt))',
'    raise last_error',
'',
'',
'def backoff_delay(attempt):',
'    return (BACKOFF_BASE_MS * 2 ** attempt) / 1000'
)

$clientFinal = As-Text @(
'import json',
'import time',
'import urllib.request',
'',
'DEFAULT_ENDPOINT = "https://auth.internal/token"',
'BACKOFF_BASE_MS = 50',
'COLD_START_FLOOR_MS = 200',
'',
'',
'def fetch_token(endpoint=DEFAULT_ENDPOINT, timeout=5, attempts=3):',
'    last_error = None',
'    for attempt in range(attempts):',
'        try:',
'            request = urllib.request.Request(endpoint, method="POST")',
'            with urllib.request.urlopen(request, timeout=timeout) as response:',
'                return json.loads(response.read())["access_token"]',
'        except OSError as error:',
'            last_error = error',
'            time.sleep(backoff_delay(attempt))',
'    raise last_error',
'',
'',
'def backoff_delay(attempt):',
'    if attempt == 0:',
'        # The credential provider is still initialising when the first attempt',
'        # runs, so attempt 0 needs a fixed floor instead of the 50ms ramp.',
'        return COLD_START_FLOOR_MS / 1000',
'    return (BACKOFF_BASE_MS * 2 ** attempt) / 1000'
)

$sessionFinal = As-Text @('import auth.client', '', 'SESSION_TTL_SECONDS = 3600', '', '', 'def open_session():',
'    token = auth.client.fetch_token()',
'    return {"token": token, "ttl": SESSION_TTL_SECONDS}'
)

$testFinal = As-Text @(
'import unittest',
'',
'from auth import client',
'',
'',
'class BackoffTest(unittest.TestCase):',
'    def test_first_attempt_waits_the_cold_start_floor(self):',
'        self.assertEqual(client.backoff_delay(0), 0.2)',
'',
'    def test_later_attempts_follow_the_ramp(self):',
'        self.assertEqual(client.backoff_delay(1), 0.1)',
'        self.assertEqual(client.backoff_delay(3), 0.4)',
'',
'',
'if __name__ == "__main__":',
'    unittest.main()'
)

$editorconfig = As-Text @('root = true', '', '[*]', 'indent_style = space', 'indent_size = 4', 'end_of_line = lf', 'insert_final_newline = true')

# --- history ---------------------------------------------------------------

Write-RepoFile (Join-Path $Target ".gitignore") $gitignore
Write-RepoFile (Join-Path $Target "src/client.py") (ConvertTo-Tabs $client1)
Write-RepoFile (Join-Path $Target "src/session.py") (ConvertTo-Tabs $session1)
Invoke-Commit "Add token client and session opener" "2024-03-04T10:12:00+08:00"

Write-RepoFile (Join-Path $Target "src/client.py") (ConvertTo-Tabs $client2)
Invoke-Commit "Retry token fetches with exponential backoff" "2024-03-05T16:40:00+08:00"

New-Item -ItemType Directory -Force -Path (Join-Path $Target "src/auth") | Out-Null
Write-RepoFile (Join-Path $Target "src/auth/__init__.py") ""
git -C $Target mv src/client.py src/auth/client.py
Write-RepoFile (Join-Path $Target "src/session.py") (ConvertTo-Tabs $sessionFinal)
Invoke-Commit "Move the token client into an auth package" "2024-03-06T09:05:00+08:00"

Write-RepoFile (Join-Path $Target "src/auth/client.py") (ConvertTo-Tabs $clientFinal)
Write-RepoFile (Join-Path $Target "src/tests/test_backoff.py") (ConvertTo-Tabs $testFinal)
Invoke-Commit "Hold attempt 0 to a fixed 200ms floor on cold start (#1)" "2024-03-12T11:27:00+08:00"

Write-RepoFile (Join-Path $Target "src/auth/client.py") $clientFinal
Write-RepoFile (Join-Path $Target "src/session.py") $sessionFinal
Write-RepoFile (Join-Path $Target "src/tests/test_backoff.py") $testFinal
Write-RepoFile (Join-Path $Target ".editorconfig") $editorconfig
Invoke-Commit "Normalise indentation to spaces to match .editorconfig" "2024-03-13T14:52:00+08:00"

Write-Output ""
Write-Output "history rebuilt at $Target"
git -C $Target log --oneline --graph
