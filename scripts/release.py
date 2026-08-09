"""Cut a release: bump the version, tag it, push, let CI do the rest.

    python scripts/release.py 1.1.0            # explicit
    python scripts/release.py --bump minor     # major | minor | patch
    python scripts/release.py --bump patch --dry-run
    python scripts/release.py 1.1.0 --no-push  # commit and tag, push by hand

This is the whole "push a new version" story. It builds nothing: pushing the
tag is what starts .github/workflows/release.yml, and the installer that ends
up on the Releases page is the one CI built on a clean Windows runner, never
one from this machine.

Before the first release from a new machine, or after touching anything under
scripts/ or installer/, run the workflow manually from Actions > Release. Run
from a branch it is always a dry run -- the whole build and every test, but
nothing published -- so a broken build costs a re-run rather than a deleted tag.

Every check below is fatal, in this order:

  * on `main`, clean working tree, in sync with origin/main
  * the new version parses as X.Y.Z and is strictly greater than the current
  * the tag vX.Y.Z exists neither locally nor on the remote
  * CHANGELOG.md has an `## Unreleased` section with something in it
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VERSION_FILE = REPO / "stashlib" / "_version.py"
CHANGELOG = REPO / "CHANGELOG.md"
REMOTE = "origin"
BRANCH = "main"
UNRELEASED = "## Unreleased"
ACTIONS_URL = "https://github.com/AmreetKumarkhuntia/stash/actions/workflows/release.yml"

VERSION_RE = re.compile(r'(?m)^(__version__\s*=\s*")([^"]+)(")$')
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def git(*arguments: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO), *arguments], capture_output=True, text=True
    )
    if check and result.returncode != 0:
        raise SystemExit(f"git {' '.join(arguments)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def parse(version: str) -> tuple[int, int, int]:
    match = SEMVER_RE.match(version)
    if not match:
        raise SystemExit(f"{version!r} is not X.Y.Z")
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def current_version() -> str:
    match = VERSION_RE.search(VERSION_FILE.read_text(encoding="utf-8"))
    if not match:
        raise SystemExit(f"no __version__ line in {VERSION_FILE}")
    return match.group(2)


def bump(current: str, part: str) -> str:
    major, minor, patch = parse(current)
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def preflight(new: str) -> None:
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != BRANCH:
        raise SystemExit(f"on {branch}; releases are cut from {BRANCH} only")

    dirty = git("status", "--porcelain")
    if dirty:
        raise SystemExit("working tree is not clean:\n" + dirty)

    git("fetch", REMOTE, BRANCH, "--tags")
    local, remote = git("rev-parse", "HEAD"), git("rev-parse", f"{REMOTE}/{BRANCH}")
    if local != remote:
        raise SystemExit(
            f"HEAD ({local[:8]}) and {REMOTE}/{BRANCH} ({remote[:8]}) have diverged — "
            "pull or push before releasing"
        )

    tag = f"v{new}"
    if git("tag", "--list", tag):
        raise SystemExit(f"tag {tag} already exists locally")
    if git("ls-remote", "--tags", REMOTE, f"refs/tags/{tag}"):
        raise SystemExit(f"tag {tag} already exists on {REMOTE}")


def changelog_body() -> str:
    if not CHANGELOG.exists():
        raise SystemExit(f"{CHANGELOG.name} is missing")
    text = CHANGELOG.read_text(encoding="utf-8", newline="")
    if UNRELEASED not in text:
        raise SystemExit(f"no '{UNRELEASED}' heading in {CHANGELOG.name}")
    rest = text.split(UNRELEASED, 1)[1]
    return rest.split("\n## ", 1)[0].strip()


def write_version(new: str) -> None:
    # newline="" preserves whatever line endings the file already has; this
    # repo is edited from both WSL and Windows.
    text = VERSION_FILE.read_text(encoding="utf-8", newline="")
    VERSION_FILE.write_text(
        VERSION_RE.sub(rf"\g<1>{new}\g<3>", text, count=1), encoding="utf-8", newline=""
    )


def promote_changelog(new: str) -> None:
    """Slide a dated heading under Unreleased, leaving Unreleased empty above."""
    text = CHANGELOG.read_text(encoding="utf-8", newline="")
    heading = f"## {new} — {date.today().isoformat()}"
    CHANGELOG.write_text(
        text.replace(UNRELEASED, f"{UNRELEASED}\n\n{heading}", 1),
        encoding="utf-8",
        newline="",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("version", nargs="?", help="the new version, X.Y.Z")
    parser.add_argument("--bump", choices=("major", "minor", "patch"))
    parser.add_argument("--dry-run", action="store_true", help="check everything, change nothing")
    parser.add_argument("--no-push", action="store_true", help="commit and tag, but do not push")
    parser.add_argument("--allow-empty-changelog", action="store_true")
    args = parser.parse_args()

    if bool(args.version) == bool(args.bump):
        raise SystemExit("give either a version or --bump, not both and not neither")

    current = current_version()
    new = args.version or bump(current, args.bump)

    if parse(new) <= parse(current):
        raise SystemExit(f"{new} is not greater than the current {current}")

    preflight(new)

    body = changelog_body()
    if not body and not args.allow_empty_changelog:
        raise SystemExit(
            f"the '{UNRELEASED}' section of {CHANGELOG.name} is empty — write "
            "what changed, or pass --allow-empty-changelog"
        )

    print(f"{current}  ->  {new}\n")
    print(body or "(no changelog entries)")
    print()

    if args.dry_run:
        print("dry run: nothing written, nothing pushed")
        return 0

    write_version(new)
    promote_changelog(new)
    git("add", "stashlib/_version.py", "CHANGELOG.md")
    git("commit", "-m", f"Release v{new}")
    git("tag", "-a", f"v{new}", "-m", f"Stash {new}")

    if args.no_push:
        print(
            f"committed and tagged. Push with:\n"
            f"    git push --atomic {REMOTE} {BRANCH} v{new}"
        )
        return 0

    # --atomic so the branch and the tag land together. A tag that arrives
    # without its commit starts a release build against a ref GitHub cannot
    # generate notes for.
    git("push", "--atomic", REMOTE, BRANCH, f"v{new}")
    print(
        f"pushed v{new}\n  {ACTIONS_URL}\n\n"
        f"If the build fails, drop the tag and try again:\n"
        f"    git push {REMOTE} :refs/tags/v{new} && git tag -d v{new}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
