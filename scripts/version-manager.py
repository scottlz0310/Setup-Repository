#!/usr/bin/env python3
"""Version management helper for releases."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = ROOT / "pyproject.toml"
INIT_PATH = ROOT / "src" / "setup_repo" / "__init__.py"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
RELEASE_NOTES_PATH = ROOT / "release-notes.md"

VERSION_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)


def _fail(message: str) -> NoReturn:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _fail(f"Missing file: {path}")


def _version_key(value: str) -> tuple[int, int, int, int, tuple[tuple[int, str | int], ...]]:
    match = VERSION_RE.match(value)
    if not match:
        _fail(f"Invalid version: {value}")

    major = int(match.group("major"))
    minor = int(match.group("minor"))
    patch = int(match.group("patch"))
    prerelease = match.group("prerelease")

    tokens: list[tuple[int, str | int]] = []
    if prerelease:
        for part in prerelease.split("."):
            if part.isdigit():
                tokens.append((0, int(part)))
            else:
                tokens.append((1, part))

    # Release versions sort after prereleases.
    is_release = 1 if prerelease is None else 0
    return (major, minor, patch, is_release, tuple(tokens))


def _extract_version(path: Path, pattern: re.Pattern[str], label: str) -> str:
    content = _read_text(path)
    match = pattern.search(content)
    if not match:
        _fail(f"Unable to find version in {label}: {path}")
    return match.group("version")


def _update_version(path: Path, pattern: re.Pattern[str], label: str, version: str) -> None:
    content = _read_text(path)

    def replacer(match: re.Match[str]) -> str:
        return f"{match.group(1)}{version}{match.group(3)}"

    updated, count = pattern.subn(replacer, content, count=1)
    if count != 1:
        _fail(f"Unable to update version in {label}: {path}")
    path.write_text(updated, encoding="utf-8")


def _get_repo_versions() -> tuple[str, str]:
    pyproject_version = _extract_version(
        PYPROJECT_PATH,
        re.compile(r'^version\s*=\s*"(?P<version>[^"]+)"', re.MULTILINE),
        "pyproject",
    )
    init_version = _extract_version(
        INIT_PATH,
        re.compile(r'^__version__\s*=\s*"(?P<version>[^"]+)"', re.MULTILINE),
        "package __init__",
    )
    return pyproject_version, init_version


def _git_tags() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "tag", "--list", "v*"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _latest_tag_version() -> str | None:
    versions: list[str] = []
    for tag in _git_tags():
        if tag.startswith("v"):
            versions.append(tag[1:])
    if not versions:
        return None
    return max(versions, key=_version_key)


def _git_rev(ref: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", ref],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return result.stdout.strip()


def _smart_check(target: str) -> None:
    pyproject_version, init_version = _get_repo_versions()
    if pyproject_version != init_version:
        _fail(f"Version mismatch: pyproject={pyproject_version}, __init__={init_version}")

    target_key = _version_key(target)
    current_key = _version_key(pyproject_version)
    if target_key < current_key:
        _fail(f"Target version {target} is lower than current {pyproject_version}")

    latest = _latest_tag_version()
    if latest and target_key < _version_key(latest):
        _fail(f"Target version {target} is lower than latest tag {latest}")

    tag_name = f"v{target}"
    if tag_name in _git_tags():
        tag_commit = _git_rev(tag_name)
        head_commit = _git_rev("HEAD")
        if tag_commit and head_commit and tag_commit != head_commit:
            _fail(f"Tag {tag_name} already exists on a different commit")

    print("Smart version check passed.")


def _check_versions() -> None:
    pyproject_version, init_version = _get_repo_versions()
    if pyproject_version != init_version:
        _fail(f"Version mismatch: pyproject={pyproject_version}, __init__={init_version}")
    _version_key(pyproject_version)
    print(f"Version check passed: {pyproject_version}")


def _set_version(version: str) -> None:
    _version_key(version)
    _update_version(
        PYPROJECT_PATH,
        re.compile(r'^(version\s*=\s*")([^"]+)(")', re.MULTILINE),
        "pyproject",
        version,
    )
    _update_version(
        INIT_PATH,
        re.compile(r'^(__version__\s*=\s*")([^"]+)(")', re.MULTILINE),
        "package __init__",
        version,
    )
    print(f"Version updated to {version}")


def _update_changelog(version: str, prerelease: bool) -> None:
    _version_key(version)
    date_str = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")

    if CHANGELOG_PATH.exists():
        content = _read_text(CHANGELOG_PATH)
    else:
        content = "# 更新履歴\n\nこのプロジェクトの主な変更点はこのファイルに記載します。\n\n"

    header = f"## [{version}] - {date_str}"
    if header in content:
        print("CHANGELOG already contains target version.")
        return

    section = [
        header,
        "",
        "### 追加",
        "",
        "- TBD",
        "",
    ]
    if prerelease:
        section.insert(2, "### プレリリース")
        section.insert(3, "")
        section.insert(4, "- TBD")
        section.insert(5, "")

    lines = content.splitlines()
    insert_at = None
    for idx, line in enumerate(lines):
        if line.startswith("## ["):
            insert_at = idx
            break
    if insert_at is None:
        insert_at = len(lines)
        if lines and lines[-1].strip():
            lines.append("")

    new_lines = lines[:insert_at] + section + lines[insert_at:]
    CHANGELOG_PATH.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
    print(f"CHANGELOG updated for {version}")


def _generate_notes(version: str, prerelease: bool) -> None:
    _version_key(version)
    changelog = _read_text(CHANGELOG_PATH)
    section_pattern = re.compile(
        rf"^## \[{re.escape(version)}\].*?$",
        re.MULTILINE,
    )
    match = section_pattern.search(changelog)
    section = ""
    if match:
        start = match.start()
        rest = changelog[start:].splitlines()
        body_lines: list[str] = []
        for line in rest[1:]:
            if line.startswith("## ["):
                break
            body_lines.append(line)
        section = "\n".join(body_lines).strip()

    lines = [f"# Release v{version}", ""]
    if prerelease:
        lines.extend(["- Prerelease", ""])
    if section:
        lines.append(section)
    else:
        lines.append("No release notes available.")

    RELEASE_NOTES_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Release notes generated: {RELEASE_NOTES_PATH}")


def _bump_version(kind: str) -> str:
    current, _ = _get_repo_versions()
    major, minor, patch, _, _ = _version_key(current)
    prerelease_match = VERSION_RE.match(current)
    prerelease = prerelease_match.group("prerelease") if prerelease_match else None

    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if kind == "prerelease":
        if prerelease:
            parts = prerelease.split(".")
            if parts and parts[-1].isdigit():
                parts[-1] = str(int(parts[-1]) + 1)
                return f"{major}.{minor}.{patch}-" + ".".join(parts)
        return f"{major}.{minor}.{patch}-beta.1"

    _fail(f"Unknown bump type: {kind}")


def _tag_and_push(version: str, push: bool) -> None:
    tag = f"v{version}"
    subprocess.run(["git", "tag", "-a", tag, "-m", f"Release {tag}"], check=True)
    print(f"Tag created: {tag}")
    if push:
        subprocess.run(["git", "push", "origin", "main"], check=True)
        subprocess.run(["git", "push", "origin", tag], check=True)
        print("Pushed main and tag.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Version management helper.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Check version consistency")
    group.add_argument("--smart-check", dest="smart_check", metavar="VERSION", help="Smart version check")
    group.add_argument("--set", dest="set_version", metavar="VERSION", help="Set version")
    group.add_argument("--update-changelog", dest="update_changelog", metavar="VERSION", help="Update changelog")
    group.add_argument("--generate-notes", dest="generate_notes", metavar="VERSION", help="Generate release notes")
    group.add_argument(
        "--bump",
        dest="bump",
        choices=["major", "minor", "patch", "prerelease"],
        help="Bump version",
    )
    parser.add_argument("--prerelease", action="store_true", help="Mark prerelease changes")
    parser.add_argument("--tag", action="store_true", help="Create git tag (requires --bump)")
    parser.add_argument("--push", action="store_true", help="Push changes (requires --tag)")

    args = parser.parse_args()

    if args.check:
        _check_versions()
        return

    if args.smart_check:
        _smart_check(args.smart_check)
        return

    if args.set_version:
        _set_version(args.set_version)
        return

    if args.update_changelog:
        _update_changelog(args.update_changelog, args.prerelease)
        return

    if args.generate_notes:
        _generate_notes(args.generate_notes, args.prerelease)
        return

    if args.bump:
        new_version = _bump_version(args.bump)
        _set_version(new_version)
        if args.tag:
            _tag_and_push(new_version, args.push)
        return

    _fail("No action specified")


if __name__ == "__main__":
    main()
