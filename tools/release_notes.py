"""
release_notes.py - Checks a release tag and writes its release notes.
=====================================================================

Used by the release workflow, and handy to run locally before tagging:

    python tools/release_notes.py v2.1.3

It refuses (exit code 1) unless the tag's version matches APP_VERSION in
config.py and CHANGELOG.md has a section for it, so a release can't go out
with the wrong version number or no notes. On success it prints the notes:
packaging/release_notes_template.md filled in with that changelog section.

A "-dryrun" suffix (e.g. v2.1.3-dryrun) is accepted and checked the same way;
the workflow uses it to test the whole pipeline without drafting a release.

Author:  TCurrie11 (https://github.com/TCurrie11)
Project: Coach Board Tool

Version history:
    2.1.3  2026-10-14  TCurrie11  Initial version.
"""
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.py"
CHANGELOG_FILE = PROJECT_ROOT / "CHANGELOG.md"
TEMPLATE_FILE = PROJECT_ROOT / "packaging" / "release_notes_template.md"
DRY_RUN_SUFFIX = "-dryrun"


class ReleaseCheckFailed(Exception):
    """The tag, config.py and CHANGELOG.md don't agree."""


def version_from_tag(tag: str) -> str:
    """'v2.1.3' or 'v2.1.3-dryrun' -> '2.1.3'."""
    match = re.fullmatch(r"v(\d+\.\d+\.\d+)(?:" + re.escape(DRY_RUN_SUFFIX) + r")?", tag)
    if not match:
        raise ReleaseCheckFailed(f"Tag {tag!r} should look like v1.2.3 (or v1.2.3{DRY_RUN_SUFFIX}).")
    return match.group(1)


def app_version() -> str:
    """APP_VERSION as written in config.py (read as text, so no Qt import needed)."""
    match = re.search(r'^APP_VERSION = "([^"]+)"', CONFIG_FILE.read_text(), re.MULTILINE)
    if not match:
        raise ReleaseCheckFailed("Couldn't find APP_VERSION in config.py.")
    return match.group(1)


def changelog_section(version: str) -> str:
    """The bullet points under '## <version> - <date>' in CHANGELOG.md."""
    heading = re.compile(rf"^## {re.escape(version)} - .*$", re.MULTILINE)
    start = heading.search(CHANGELOG_FILE.read_text())
    if not start:
        raise ReleaseCheckFailed(f"CHANGELOG.md has no '## {version} - <date>' section.")
    rest = CHANGELOG_FILE.read_text()[start.end():]
    next_heading = re.search(r"^## ", rest, re.MULTILINE)
    return (rest[:next_heading.start()] if next_heading else rest).strip()


def release_notes(tag: str) -> str:
    version = version_from_tag(tag)
    if app_version() != version:
        raise ReleaseCheckFailed(
            f"Tag {tag} doesn't match APP_VERSION {app_version()!r} in config.py. "
            "Bump APP_VERSION (and add a CHANGELOG.md section) before tagging.")
    # str.replace rather than str.format: changelog text may contain braces.
    return (TEMPLATE_FILE.read_text()
            .replace("{version}", version)
            .replace("{changes}", changelog_section(version)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python tools/release_notes.py v1.2.3")
    try:
        print(release_notes(sys.argv[1]))
    except ReleaseCheckFailed as problem:
        sys.exit(f"Release check failed: {problem}")
