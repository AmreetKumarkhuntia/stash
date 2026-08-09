"""Build a distributable Setup.exe with install/uninstall support.

    python.exe scripts/build_installer.py                        # app + installer
    python.exe scripts/build_installer.py --skip-app             # reuse the last app build
    python.exe scripts/build_installer.py --build-root D:\tmp\b  # build somewhere else

Runs PyInstaller first (via build_exe.py), then compiles installer/*.iss with
Inno Setup's command-line compiler. The result is a single file you can hand to
anyone: it installs per-user with no admin rights, adds Start Menu and optional
Desktop shortcuts, and registers a proper entry in Windows "Installed apps" so
it can be uninstalled the normal way.

The version comes from stashlib/_version.py and is passed through to Inno as
/DAppVersion, so it lands in the installer filename, the "Installed apps" entry
and the exe's file properties without being written down anywhere twice.

Inno Setup is the only extra tool needed:  winget install JRSoftware.InnoSetup
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

APP_NAME = "Stash"
PLUGIN_DIR = Path(__file__).resolve().parent.parent


def _iscc_candidates() -> list[Path]:
    roots = [
        Path(r"C:\Program Files (x86)"),
        Path(r"C:\Program Files"),
    ]
    # winget installs Inno Setup per-user by default, which puts it under
    # %LOCALAPPDATA%\Programs rather than Program Files.
    local = os.environ.get("LOCALAPPDATA")
    if local:
        roots.insert(0, Path(local) / "Programs")
    return [root / f"Inno Setup {v}" / "ISCC.exe" for root in roots for v in (6, 7)]


def find_iscc() -> Path | None:
    for candidate in _iscc_candidates():
        if candidate.exists():
            return candidate
    from shutil import which

    found = which("ISCC.exe")
    return Path(found) if found else None


def default_build_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or "."
    return Path(base) / APP_NAME / "build"


def app_version() -> str:
    """The version from stashlib/_version.py — the only place it lives."""
    sys.path.insert(0, str(PLUGIN_DIR))
    from stashlib._version import __version__

    return __version__


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-app", action="store_true", help="reuse the existing app build")
    # %% because argparse runs help strings through %-formatting.
    parser.add_argument("--build-root", type=Path, default=None,
                        help=r"where the app is built (default %%LOCALAPPDATA%%\Stash\build)")
    parser.add_argument("--outdir", type=Path, default=None,
                        help=r"where to write Setup.exe (default <build-root>\installer)")
    parser.add_argument("--app-version", default=None,
                        help="override the version (default: stashlib/_version.py)")
    parser.add_argument("--sign-command", default=None,
                        help="Inno SignTool command; $f is the file to sign")
    args = parser.parse_args()

    plugin_dir = PLUGIN_DIR
    script = plugin_dir / "installer" / "Stash.iss"

    iscc = find_iscc()
    if iscc is None:
        print(
            "Inno Setup not found. Install it with:\n"
            "    winget install JRSoftware.InnoSetup\n"
            "then run this again."
        )
        return 1

    build_root = (args.build_root or default_build_root()).resolve()
    version = args.app_version or app_version()

    if not args.skip_app:
        print("=== building the app with PyInstaller ===")
        # --outdir must be passed explicitly: build_exe.py and this script both
        # default to the same place, but only by coincidence, and a --build-root
        # that only reached one of them would build fine and package nothing.
        command = [
            sys.executable, str(plugin_dir / "scripts" / "build_exe.py"),
            "--outdir", str(build_root),
            "--app-version", version,
        ]
        if args.sign_command:
            command += ["--sign-command", args.sign_command]
        result = subprocess.run(command)
        if result.returncode != 0:
            return result.returncode

    source = build_root / "dist" / APP_NAME
    if not (source / f"{APP_NAME}.exe").exists():
        print(f"App build not found at {source}. Run without --skip-app first.")
        return 1

    outdir = (args.outdir or (build_root / "installer")).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    print("\n=== compiling the installer ===")
    command = [
        str(iscc),
        f"/DAppVersion={version}",
        f"/DSourceDir={source}",
        f"/DOutputDir={outdir}",
    ]
    if args.sign_command:
        command += ["/DSign", f"/Sstashsign={args.sign_command}"]
    command.append(str(script))
    result = subprocess.run(command)
    if result.returncode != 0:
        print("\nInstaller compile failed — see the output above.")
        return result.returncode

    # An exact name rather than sorted(glob())[-1], which picked the
    # lexicographically last file: a stale Stash-Setup-1.9.0.exe in the folder
    # would beat the 1.10.0 just built. It also proves /DAppVersion reached the
    # .iss instead of it silently falling back to the literal in the script.
    installer = outdir / f"{APP_NAME}-Setup-{version}.exe"
    if not installer.exists():
        print(f"\nExpected {installer} but it was not produced.")
        return 1

    size = installer.stat().st_size / 1_000_000
    print(f"\nInstaller: {installer}  ({size:.0f} MB)")
    print("\nHand that single file to anyone. It installs per-user (no admin),")
    print("and uninstalls from Settings > Apps > Installed apps.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
