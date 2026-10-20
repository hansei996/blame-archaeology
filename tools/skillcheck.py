#!/usr/bin/env python3
"""Structural guardrails for a single-skill agent repository.

Standard library only: CI needs nothing beyond the interpreter, no pip install.

Usage:
    python tools/skillcheck.py [REPO_ROOT] [--name REPO_NAME]

REPO_ROOT  defaults to the parent of the directory holding this script.
REPO_NAME  defaults to the last path segment of $GITHUB_REPOSITORY (set by
           GitHub Actions), then to the basename of REPO_ROOT.

Every check prints one PASS/FAIL line. Exit code is 0 only when all pass.
"""

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

MAX_BODY_LINES = 70
MAX_RULES = 12
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".mypy_cache"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RULE_RE = re.compile(r"^\s*(\d+)\.\s+\S")
HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
REQUIRED_FRONTMATTER_KEYS = ("name", "description", "license")
MAX_SCAN_BYTES = 2 * 1024 * 1024
PLUGIN_DIR = "." + "claude-plugin"

RESULTS = []


def record(passed_flag, check_id, detail):
    RESULTS.append((passed_flag, check_id, detail))
    return passed_flag


def passed(check_id, detail):
    return record(True, check_id, detail)


def failed(check_id, detail):
    return record(False, check_id, detail)


def rel(path, root):
    try:
        return Path(path).relative_to(root).as_posix()
    except ValueError:
        return str(path)


def read_text(path):
    return path.read_text(encoding="utf-8-sig")


def strip_scalar(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def parse_frontmatter(text):
    """Return (mapping, body_lines, error).

    Supports the top-level "key: value" subset of YAML a SKILL.md header uses:
    plain or quoted scalars, comments, and indented continuation lines folded
    into the previous value. Nested maps and sequences are out of scope.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, None, "file does not start with a '---' frontmatter fence"
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, None, "frontmatter fence is never closed with '---'"

    data = {}
    last_key = None
    for offset, raw in enumerate(lines[1:end], start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[0] in " \t":
            if last_key is None:
                return None, None, "frontmatter line %d: indented value with no parent key" % offset
            data[last_key] = (data[last_key] + " " + raw.strip()).strip()
            continue
        if ":" not in raw:
            return None, None, "frontmatter line %d: expected 'key: value', got %r" % (offset, raw)
        key, value = raw.split(":", 1)
        key = key.strip()
        value = strip_scalar(value.strip())
        if not key:
            return None, None, "frontmatter line %d: empty key" % offset
        if key in data:
            return None, None, "frontmatter line %d: duplicate key %r" % (offset, key)
        data[key] = value
        last_key = key
    return data, lines[end + 1:], None


def check_rules(body):
    start = None
    for i, line in enumerate(body):
        if re.match(r"^##\s+Rules\s*$", line.strip(), re.IGNORECASE):
            start = i + 1
            break
    if start is None:
        return failed("skill.rules", "no '## Rules' section in the SKILL.md body")
    numbers = []
    for line in body[start:]:
        heading = HEADING_RE.match(line.strip())
        if heading and len(heading.group(1)) <= 2:
            break
        match = RULE_RE.match(line)
        if match:
            numbers.append(int(match.group(1)))
    if not numbers:
        return failed("skill.rules", "'## Rules' section has no numbered rules")
    if len(numbers) > MAX_RULES:
        return failed("skill.rules", "%d numbered rules, limit is %d" % (len(numbers), MAX_RULES))
    if numbers != list(range(1, len(numbers) + 1)):
        return failed("skill.rules", "rule numbering is not 1..%d: %s" % (len(numbers), numbers))
    return passed("skill.rules", "%d numbered rules (limit %d), numbered 1..%d"
                  % (len(numbers), MAX_RULES, len(numbers)))


def check_frontmatter(root, repo):
    skill_path = root / "skills" / repo / "SKILL.md"
    if not skill_path.is_file():
        return failed("skill.path", "missing skills/%s/SKILL.md" % repo)
    passed("skill.path", "found %s" % rel(skill_path, root))

    data, body, error = parse_frontmatter(read_text(skill_path))
    if error is not None:
        return failed("skill.frontmatter", error)
    passed("skill.frontmatter", "frontmatter parsed (%d keys, YAML key: value subset)" % len(data))

    missing = [k for k in REQUIRED_FRONTMATTER_KEYS if not str(data.get(k, "")).strip()]
    if missing:
        failed("skill.frontmatter.keys", "missing or empty: %s" % ", ".join(missing))
    else:
        passed("skill.frontmatter.keys", "name / description / license present and non-empty")

    name = str(data.get("name", "")).strip()
    if name != repo:
        failed("skill.name", "frontmatter name %r != repository %r" % (name, repo))
    elif not SLUG_RE.match(name):
        failed("skill.name", "frontmatter name %r is not a lowercase hyphenated slug" % name)
    else:
        passed("skill.name", "frontmatter name %r matches repository name" % name)

    body = list(body)
    while body and not body[-1].strip():
        body.pop()
    if len(body) > MAX_BODY_LINES:
        failed("skill.body", "body is %d lines, limit is %d" % (len(body), MAX_BODY_LINES))
    else:
        passed("skill.body", "body is %d lines (limit %d)" % (len(body), MAX_BODY_LINES))

    check_rules(body)


def check_manifest(root, repo, relative, check_id):
    path = root / relative
    if not path.is_file():
        failed(check_id, "missing %s" % relative)
        return None
    try:
        data = json.loads(read_text(path))
    except (ValueError, OSError) as exc:
        failed(check_id, "not parsable JSON: %s" % exc)
        return None
    if not isinstance(data, dict):
        failed(check_id, "top-level JSON value is not an object")
        return None
    passed(check_id, "%s is parsable JSON (%d top-level keys)" % (relative, len(data)))
    name = data.get("name")
    if not isinstance(name, str) or name.strip() != repo:
        failed(check_id + ".name", "name %r != repository %r" % (name, repo))
    else:
        passed(check_id + ".name", "name %r matches repository" % name)
    return data


def check_plugin_manifests(root, repo):
    check_manifest(root, repo, PLUGIN_DIR + "/plugin.json", "manifest.plugin.json")
    marketplace = check_manifest(root, repo, PLUGIN_DIR + "/marketplace.json",
                                 "manifest.marketplace.json")
    if marketplace is None:
        return
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        failed("manifest.marketplace.plugins", "plugins is missing or not a non-empty list")
        return
    first = plugins[0]
    if not isinstance(first, dict) or not str(first.get("name", "")).strip():
        failed("manifest.marketplace.plugins[0]", "plugins[0] has no non-empty name")
        return
    passed("manifest.marketplace.plugins[0]", "plugins[0].name is %r" % first["name"])


def is_relative_link(target):
    value = target.strip()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1].strip()
    if not value or value.startswith("#"):
        return None
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", value) or value.startswith("//"):
        return None
    value = value.split("#", 1)[0].split("?", 1)[0]
    value = unquote(value).strip()
    return value or None


def check_readme_links(root):
    readme = root / "README.md"
    if not readme.is_file():
        return failed("readme.path", "missing README.md")
    targets = []
    for lineno, line in enumerate(read_text(readme).splitlines(), start=1):
        for raw in LINK_RE.findall(line):
            value = is_relative_link(raw)
            if value is not None:
                targets.append((lineno, value))
    if not targets:
        return failed("readme.links", "README.md contains no relative links to check")
    broken = ["line %d -> %s" % (lineno, value)
              for lineno, value in targets if not (root / value).exists()]
    if broken:
        failed("readme.links", "%d of %d relative links are broken: %s"
               % (len(broken), len(targets), "; ".join(broken)))
    else:
        passed("readme.links", "all %d relative README links resolve" % len(targets))

    skill_links = [v for _, v in targets if re.search(r"(^|/)skills/[^/]+/SKILL\.md$", v)]
    if not skill_links:
        failed("readme.skill-link", "README.md does not link to skills/<name>/SKILL.md")
    else:
        passed("readme.skill-link", "README.md links to %s" % skill_links[0])


def placeholder_patterns():
    return [
        ("angle-bracket '<' 'you' '>' placeholder",
         re.compile("<" + "you" + ">", re.IGNORECASE)),
        ("TO-DO / FIX-ME marker",
         re.compile(r"\b(?:TO" + "DO|FIX" + r"ME)\b")),
    ]


def iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            yield Path(dirpath) / name


def scan_placeholders(root):
    patterns = placeholder_patterns()
    findings = []
    scanned = 0
    for path in iter_files(root):
        try:
            if path.stat().st_size > MAX_SCAN_BYTES:
                continue
            raw = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in raw[:8192]:
            continue
        scanned += 1
        for lineno, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), start=1):
            for label, pattern in patterns:
                if pattern.search(line):
                    findings.append("%s:%d: %s" % (rel(path, root), lineno, label))
    if findings:
        failed("repo.placeholders", "%d placeholder hit(s): %s"
               % (len(findings), "; ".join(findings)))
    else:
        passed("repo.placeholders", "no placeholder residue across %d text files" % scanned)


def resolve_inputs(argv):
    name_override = None
    positional = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--name":
            i += 1
            if i >= len(argv):
                print("error: --name needs a value", file=sys.stderr)
                return None, None
            name_override = argv[i]
        elif arg.startswith("--name="):
            name_override = arg.split("=", 1)[1]
        elif arg in ("-h", "--help"):
            print(__doc__)
            return None, None
        else:
            positional.append(arg)
        i += 1
    if len(positional) > 1:
        print("error: at most one REPO_ROOT argument is accepted", file=sys.stderr)
        return None, None
    root = Path(positional[0]).resolve() if positional else Path(__file__).resolve().parent.parent
    repo = (name_override
            or os.environ.get("GITHUB_REPOSITORY", "").rsplit("/", 1)[-1].strip()
            or root.name)
    return root, repo


def main(argv):
    root, repo = resolve_inputs(argv[1:])
    if root is None:
        return 0
    print("skillcheck")
    print("  repository : %s" % repo)
    print("  root       : %s" % root)
    print("  python     : %s" % sys.version.split()[0])
    print("")
    if not root.is_dir():
        print("[FAIL] %-32s root directory does not exist: %s" % ("repo.root", root))
        print("")
        print("0 passed, 1 failed.")
        print("RESULT: FAIL")
        return 1

    check_frontmatter(root, repo)
    check_plugin_manifests(root, repo)
    check_readme_links(root)
    scan_placeholders(root)

    width = max(len(item[1]) for item in RESULTS)
    for passed_flag, check_id, detail in RESULTS:
        print("[%s] %s  %s" % ("PASS" if passed_flag else "FAIL", check_id.ljust(width), detail))

    failures = [item for item in RESULTS if not item[0]]
    print("")
    if failures:
        print("%d passed, %d failed." % (len(RESULTS) - len(failures), len(failures)))
        print("RESULT: FAIL")
        return 1
    print("%d passed, 0 failed." % len(RESULTS))
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
