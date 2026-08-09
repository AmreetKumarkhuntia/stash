# Changelog

Written by hand; `scripts/release.py` only promotes the Unreleased heading and
stamps the date. Every release on
[the Releases page](https://github.com/AmreetKumarkhuntia/stash/releases)
carries the section below its version.

## Unreleased

- CI/CD: tagging `vX.Y.Z` now builds the installer on a clean Windows runner
  and publishes it to GitHub Releases, with the version coming from a single
  place (`stashlib/_version.py`).
- `Stash.exe --selftest` checks a build end to end — Qt Multimedia, the bundled
  ffmpeg, `style.qss`, and an actual waveform render — and CI runs it on both
  the unpacked app and the installed one.
- `scripts/build_installer.py` gained `--build-root`, so the app build and the
  installer no longer have to live under `%LOCALAPPDATA%`.
- Fixed: `build_installer.py` picked the installer to report by lexicographic
  name, so `Stash-Setup-1.9.0.exe` would have beaten `Stash-Setup-1.10.0.exe`.

## 1.0.0 — 2026-08-09

First tagged release. Searchable media library that drags into DaVinci Resolve:
filename normalisation, audio/video/image thumbnails, audition, favourites and
tags, global hotkey, per-user Windows installer.
