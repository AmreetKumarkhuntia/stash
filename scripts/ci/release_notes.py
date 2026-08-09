"""Compose the body of a GitHub Release.

Called from .github/workflows/release.yml. It is Python rather than a
PowerShell here-string because markdown fences are backticks and backtick is
PowerShell's escape character -- a fenced block inside @"..."@ mangles itself
silently.

gh appends its own --generate-notes output (the commit and PR list) after
whatever this writes, so this file only has to carry the part a human wants
first: how to install it, and why Windows is about to shout.
"""

from __future__ import annotations

import argparse
from pathlib import Path

TEMPLATE = """\
### Install

Download **{filename}** below and run it. It installs per-user into
`%LOCALAPPDATA%\\Programs\\Stash` — no admin rights, no Python needed.

Windows SmartScreen will say *"Windows protected your PC"*, because this build
is not code-signed. Choose **More info → Run anyway**. If you would rather
check the download first:

```powershell
(Get-FileHash -Algorithm SHA256 .\\{filename}).Hash
```

Expected:

```
{sha256}
```

Installing over an existing copy upgrades it in place and keeps your library
index, favourites and tags in `%LOCALAPPDATA%\\Stash\\library`.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    args.out.write_text(
        TEMPLATE.format(filename=args.installer.name, sha256=args.sha256),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
