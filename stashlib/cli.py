"""Dev harness for the library core — no Qt involved.

    python.exe -m stashlib.cli scan
    python.exe -m stashlib.cli search "air horn"
    python.exe -m stashlib.cli search whoosh --kind audio --limit 10
    python.exe -m stashlib.cli search "green screen" --tag overlay --root D:\\videos
    python.exe -m stashlib.cli roots
    python.exe -m stashlib.cli roots --add "D:\\videos\\overlays" --label Overlays
    python.exe -m stashlib.cli tag "Vine Boom" bruh reaction
    python.exe -m stashlib.cli tag "Vine Boom" --clear

This is how the ranker gets tuned: change a weight, re-run the golden queries,
compare. It exists before the GUI on purpose.
"""

from __future__ import annotations

import argparse
import sys
import time

from . import config
from .library import Library


def _fmt_duration(seconds: float | None) -> str:
    if not seconds:
        return "     "
    return f"{seconds:5.1f}s"


def cmd_scan(lib: Library, args) -> int:
    started = time.perf_counter()

    # Progress goes to stdout, not stderr: the probe pass mutes fd 2 to hide
    # libmpg123's ID3 chatter, which would swallow these too.
    def progress(phase: str, done: int, total: int) -> None:
        if phase == "probe" and total:
            print(f"\r  probing {done}/{total}", end="", flush=True)

    summary = lib.refresh(progress)
    print()
    elapsed = time.perf_counter() - started
    for key, value in summary.items():
        print(f"{key:>18}: {value}")
    counts = lib.counts()
    print(f"{'by kind':>18}: {counts['by_kind']}")
    print(f"{'elapsed':>18}: {elapsed:.2f}s")
    print(f"{'database':>18}: {config.db_path()}")
    return 0


def _resolve_roots(lib: Library, wanted: list[str]) -> frozenset[str] | None:
    """Map --root arguments onto the root paths actually stored.

    Query.roots compares `item.root` by exact string, and Windows paths vary in
    case and trailing slash, so a raw pass-through would silently return
    nothing. Match on the stored path or the label instead, and say so when
    there is no such root.
    """
    known = lib.roots()
    resolved: set[str] = set()
    for name in wanted:
        needle = name.rstrip("\\/").lower()
        hit = next(
            (
                root["path"]
                for root in known
                if root["path"].lower() == needle or root["label"].lower() == needle
            ),
            None,
        )
        if hit is None:
            print(f"no such root: {name}", file=sys.stderr)
            print("known roots:", file=sys.stderr)
            for root in known:
                print(f"  {root['label']:<12} {root['path']}", file=sys.stderr)
            return None
        resolved.add(hit)
    return frozenset(resolved)


def _print_tags(item) -> None:
    print(item.stem)
    print(f"  user tags: {item.user_tags or '(none)'}")
    print(f"  all tags : {' '.join(sorted(item.tags))}")


def _find_item(lib: Library, target: str):
    """Resolve a path or a filename to exactly one item, or explain why not."""
    needle = target.lower()
    for item in lib.items:
        if item.path.lower() == needle:
            return item

    matches = [i for i in lib.items if i.stem.lower() == needle]
    if not matches:
        matches = [i for i in lib.items if needle in i.stem.lower()]
    if len(matches) == 1:
        return matches[0]

    if not matches:
        print(f"nothing matches {target!r}", file=sys.stderr)
        return None
    print(f"{len(matches)} items match {target!r} — be more specific:", file=sys.stderr)
    for item in matches[:10]:
        print(f"  {item.path}", file=sys.stderr)
    return None


def cmd_search(lib: Library, args) -> int:
    roots = _resolve_roots(lib, args.root)
    if roots is None:
        return 1
    started = time.perf_counter()
    hits = lib.search(
        text=" ".join(args.query),
        kind=args.kind,
        tags=frozenset(t.lower() for t in args.tag),
        favorites_only=args.favorites,
        roots=roots,
        limit=args.limit,
    )
    elapsed = (time.perf_counter() - started) * 1000
    for item in hits:
        star = "*" if item.favorite else " "
        print(
            f"{star} {item.kind:<5} {_fmt_duration(item.duration)}  "
            f"{item.stem[:58]:<58}  {item.rel_dir}"
        )
    print(
        f"\n{len(hits)} hit(s) of {len(lib.items)} items in {elapsed:.1f} ms",
        file=sys.stderr,
    )
    return 0


def cmd_roots(lib: Library, args) -> int:
    if args.add:
        lib.add_root(args.add, args.label)
        print(f"added {args.add}")
    if args.remove:
        lib.remove_root(args.remove)
        print(f"removed {args.remove}")
    counts: dict[str, int] = {}
    for item in lib.items:
        counts[item.root] = counts.get(item.root, 0) + 1
    for root in lib.roots():
        flag = " " if root["enabled"] else "-"
        print(f"{flag} {counts.get(root['path'], 0):>6}  {root['label']:<12} {root['path']}")
    return 0


def cmd_tags(lib: Library, args) -> int:
    for tag, count in lib.top_tags(lib.items, limit=args.limit):
        print(f"{count:>6}  {tag}")
    return 0


def cmd_tag(lib: Library, args) -> int:
    """Show or set one file's own tags — the write half of tag source #3."""
    item = _find_item(lib, args.target)
    if item is None:
        return 1
    if args.clear:
        lib.set_user_tags(item, "")
    elif args.tags:
        lib.set_user_tags(item, " ".join(" ".join(args.tags).split()))
    _print_tags(item)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="stashlib", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("scan", help="rescan roots and probe new files")

    search = sub.add_parser("search", help="ranked search")
    search.add_argument("query", nargs="*", default=[])
    search.add_argument("--kind", choices=["audio", "video", "image"])
    search.add_argument("--favorites", action="store_true")
    search.add_argument(
        "--tag",
        action="append",
        default=[],
        metavar="TAG",
        help="require this tag; repeat to require several",
    )
    search.add_argument(
        "--root",
        action="append",
        default=[],
        metavar="PATH-OR-LABEL",
        help="restrict to this root; repeat to allow several",
    )
    search.add_argument("--limit", type=int, default=20)

    roots = sub.add_parser("roots", help="list or edit library roots")
    roots.add_argument("--add", metavar="PATH")
    roots.add_argument("--label", metavar="NAME")
    roots.add_argument("--remove", metavar="PATH")

    tags = sub.add_parser("tags", help="most common tags")
    tags.add_argument("--limit", type=int, default=40)

    tag = sub.add_parser("tag", help="show or set one file's own tags")
    tag.add_argument("target", metavar="PATH-OR-NAME")
    tag.add_argument("tags", nargs="*", default=[], help="replaces the current set")
    tag.add_argument("--clear", action="store_true", help="remove all of them")

    args = parser.parse_args(argv)
    lib = Library()
    try:
        return {
            "scan": cmd_scan,
            "search": cmd_search,
            "roots": cmd_roots,
            "tags": cmd_tags,
            "tag": cmd_tag,
        }[args.command](lib, args)
    finally:
        lib.close()


if __name__ == "__main__":
    raise SystemExit(main())
