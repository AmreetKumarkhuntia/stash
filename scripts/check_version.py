"""Guard the one place the version lives.

    python scripts/check_version.py                    # well-formed?
    python scripts/check_version.py --print            # -> 1.2.3
    python scripts/check_version.py --expect-tag v1.2.3

The last form is what makes it impossible to publish Stash-Setup-1.0.0.exe
under the tag v1.2.3. CI runs it as the first step of the release job, so a
mismatch costs two seconds rather than twelve minutes and a bad release.

It reads stashlib/_version.py with a regex instead of importing it, so it works
from any directory and cannot be broken by an import error elsewhere in the
package.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VERSION_FILE = REPO / "stashlib" / "_version.py"
VERSION_RE = re.compile(r'^__version__\s*=\s*"(?P<version>[^"]+)"\s*$', re.M)
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def read_version() -> str:
    match = VERSION_RE.search(VERSION_FILE.read_text(encoding="utf-8"))
    if not match:
        raise SystemExit(f'no `__version__ = "..."` line in {VERSION_FILE}')
    return match.group("version")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print", dest="do_print", action="store_true")
    parser.add_argument("--expect-tag", default=None, metavar="vX.Y.Z")
    args = parser.parse_args()

    version = read_version()

    if not SEMVER_RE.match(version):
        print(
            f"version {version!r} in {VERSION_FILE} is not X.Y.Z.\n"
            "Suffixes are not supported: the Windows VERSIONINFO resource needs "
            "four integers.",
            file=sys.stderr,
        )
        return 1

    if args.expect_tag is not None and args.expect_tag != f"v{version}":
        print(
            f"tag {args.expect_tag} does not match stashlib/_version.py ({version}).\n"
            f"Expected tag v{version}. Either bump the version file and re-tag, or\n"
            f"delete the tag:  git push origin :refs/tags/{args.expect_tag}",
            file=sys.stderr,
        )
        return 1

    if args.do_print:
        print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
