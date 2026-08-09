# Stash

A media library for video editing. Point it at your folders of meme clips,
sound effects, green screens and overlays; it indexes and categorises them,
makes them searchable, lets you preview them, and **drags them straight into
DaVinci Resolve**.

It is fully standalone — no plugin host, no Resolve scripting API, and it does
**not** need DaVinci Resolve Studio. It works on the free edition, because it
talks to Resolve the same way Windows Explorer does.

---

## Install

[**Download the latest installer**](https://github.com/AmreetKumarkhuntia/stash/releases/latest)
— one file, ~77 MB, no Python needed. It installs per-user into
`%LOCALAPPDATA%\Programs\Stash` with no admin rights, and uninstalls from
Settings → Apps → Installed apps.

Windows SmartScreen shows *"Windows protected your PC"* the first time, because
the build is not code-signed. **More info → Run anyway.** Every release ships a
`SHA256SUMS.txt` next to the installer if you would rather verify the download
first:

```powershell
(Get-FileHash -Algorithm SHA256 .\Stash-Setup-1.0.0.exe).Hash
```

Each installer is built and smoke-tested on a clean Windows runner by
[the release workflow](.github/workflows/release.yml), never uploaded from a
developer machine.

## Install from source

Double-click **`install.bat`**.

It finds your Python, installs the dependencies (~250 MB of Qt the first time),
draws the app icon, and puts a shortcut on your Desktop and in the Start Menu.

If you'd rather do it by hand:

```
python.exe -m pip install -r requirements.txt
python.exe scripts/make_icon.py
python.exe scripts/install_shortcut.py
```

Needs **Python 3.10+** on Windows. It must be a *Windows* Python — the panel
drags files into Resolve through a native Windows drag, so a WSL or MSYS Python
cannot host it. If you have several, any one on `PATH` will do.

## Run

Any of these:

- the **Desktop / Start Menu shortcut** created by the installer
- double-click **`run_panel.bat`**
- `python.exe -m panel` from this folder

First launch asks you to pick folders. Point it at anything — memes, SFX packs,
green screens, overlays, gifs, thumbnails. Sub-folders are included and their
names become searchable tags automatically, so a file in
`SFX Pack\Alarm & Chime\` is findable by typing `alarm` or `chime`.

## Getting things into Resolve

**Drag the tile out of the panel and drop it where you want it.** That's it.

| Drop it on | What happens |
|---|---|
| the **Media Pool** | the file is imported as a clip — the reliable path |
| the **timeline** | it lands as a clip at the drop point |
| an **audio track** | drop sound effects straight onto A1/A2 |

Select several tiles with Ctrl or Shift and drag them all at once. The panel
fades to 25% while you drag so you can see what you're aiming at.

There is no Resolve API involved — the panel puts a normal Windows file drag
(`CF_HDROP`) on the clipboard, byte-for-byte what Explorer produces. That is why
it works without Studio, and it is the same trick the commercial panels (SNS
ShareBrowser, Sony Ci) use. Verified with `scripts/spike_drag.py`, which stays
here as the regression harness: if a Resolve update ever breaks dragging, run it
and you'll know in ten seconds whether it's Resolve or the panel.

**Tip:** keep the panel always-on-top (the 📌 button) beside Resolve, or leave it
minimised and summon it with **Ctrl+Shift+M**, type, drag, and it gets out of
the way.

## Keys

| Key | Action |
|---|---|
| type anything | live search |
| `↑ ↓ ← →` | move through results — sounds auto-play as you go |
| `Space` | play / stop the selected item |
| `F` | favourite |
| `Ctrl+1..4` | All / Video / Audio / Image |
| `Ctrl+F` | jump to the search box |
| `Ctrl+C` | copy the file path |
| `Ctrl+R` | rescan folders |
| `Esc` | clear the search, or minimise |
| `Ctrl+Shift+M` | summon the panel over Resolve from anywhere |

Buttons: **★** favourites only · **🔊** auto-play on/off · **▤** compact mode ·
**📌** always on top · **＋** folders · **⟳** rescan.

## Search

Filenames in a real SFX pack are hostile to plain matching, so every name is
normalised first:

| On disk | Searchable as |
|---|---|
| `WaterPourChalice_S011WR.87.mp3` | `water pour chalice` |
| `MMFX_CHIME BRIGHT PERCUSSIVE_SB01.174.mp3` | `chime bright percussive` |
| `Ah Shit Here We Go Again - GTA Sound Effect (HD) ( 160kbps ).mp3` | `ah shit here we go again gta` |
| `yt1s.com - Best Rage Of The Day  Episode 11_1080p.mp4` | `best rage of the day episode 11` |

Vendor serials, ripper-site tags, bitrate/resolution noise and glued CamelCase
all get stripped, so typing what you actually mean finds the file.

**Aliases** let you name things the way you think of them. Edit
`%LOCALAPPDATA%\Stash\library\tags.json`:

```json
{
  "aliases": { "vine boom": ["bass boost", "bruh"] },
  "path_tags": { "D:\\videos\\meme\\Green Screen": ["greenscreen", "chroma"] },
  "hide": ["*.sfk", "*.url", "desktop.ini"]
}
```

Now typing `bruh` finds `Bass Boost.mp3`.

## Folders

Click **＋** to add or remove folders at any time. Removing a folder keeps your
favourites and tags, so re-adding it restores them.

The index and thumbnail cache live in
`%LOCALAPPDATA%\Stash\library\` — never inside this folder, so you can
move or reinstall the plugin without losing anything. Delete that folder to
start clean.

## Distributing it — installer with uninstall

```
python.exe scripts/build_installer.py
```

Produces **one file**, `Stash-Setup-<version>.exe` (~77 MB), under
`%LOCALAPPDATA%\Stash\build\installer\` — the version comes from
`stashlib/_version.py`. Send that to anyone. It:

- installs **per-user, with no admin rights** (into `%LOCALAPPDATA%\Programs`)
- creates Start Menu and optional Desktop shortcuts
- registers properly in **Settings → Apps → Installed apps**, so it uninstalls
  like any other program
- needs **no Python** on the target machine

Needs Inno Setup once on the *build* machine:
`winget install JRSoftware.InnoSetup`. Use `--skip-app` to recompile just the
installer from the last app build (~40 s instead of ~5 min), or `--build-root`
to build somewhere other than `%LOCALAPPDATA%\Stash\build`.

To check a build without installing it, run the shipped smoke test — it
verifies Qt Multimedia, the bundled ffmpeg, `style.qss` and a real waveform
render inside the frozen binary, and exits non-zero if anything is missing:

```
pwsh scripts\ci\selftest.ps1 -Exe "%LOCALAPPDATA%\Stash\build\dist\Stash\Stash.exe"
```

Silent install / uninstall, for scripted deployment:

```
Stash-Setup-1.2.3.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
"%LOCALAPPDATA%\Programs\Stash\unins000.exe" /VERYSILENT
```

CI runs exactly this round trip on every release, and checks that a silent
uninstall leaves your library data alone.

**Uninstalling never touches your library data unless you say so.** An
interactive uninstall asks whether to also delete the index, thumbnails,
favourites and tags in `%LOCALAPPDATA%\Stash\library\`, defaulting to
keeping them. A *silent* uninstall always keeps them — `/SUPPRESSMSGBOXES`
answers prompts with Yes regardless of the declared default, so the script skips
the question entirely rather than risk deleting data unattended.

### Just the app folder, no installer

```
python.exe scripts/build_exe.py
```

A one-folder app (~245 MB) under `%LOCALAPPDATA%\Stash\build\dist\`. Zip
and send; they double-click `Stash.exe`. `--onefile` makes a single
executable (slower to start — it unpacks each run), `--outdir` builds elsewhere.

> Not a DLL, deliberately. A DLL is loaded *by* a host process and cannot be
> launched or installed on its own; there is no host here. Resolve's only
> DLL-shaped plugins are OFX effects, which process frames and cannot draw a
> browser UI.

## Releasing

The version lives in exactly one place, `stashlib/_version.py`. Everything else
— the Inno `AppVersion`, the installer filename, the exe's file properties, the
"Installed apps" entry, the git tag — is derived from it.

```
python scripts/release.py --bump minor
```

That bumps the file, stamps `CHANGELOG.md`, commits, tags `vX.Y.Z` and pushes.
The tag starts [`release.yml`](.github/workflows/release.yml), which on a clean
Windows runner builds the app and installer, runs the frozen binary's
`--selftest`, installs it, runs the selftest again on the *installed* copy,
uninstalls it, and then publishes `Stash-Setup-X.Y.Z.exe` plus `SHA256SUMS.txt`
to a new GitHub Release. Any step failing means nothing is published.

Write what changed under `## Unreleased` in `CHANGELOG.md` first — `release.py`
refuses to cut a release with an empty section. Use `--dry-run` to check
everything without touching the repo, and `1.2.3` instead of `--bump` to set an
exact version.

Before the first release from a new machine, or after changing anything under
`scripts/` or `installer/`, run the workflow by hand from **Actions → Release →
Run workflow** with `publish` unchecked: same build, same tests, nothing
published. A tag that fails to build is deleted with
`git push origin :refs/tags/vX.Y.Z && git tag -d vX.Y.Z`.

Releases are **not code-signed**, so SmartScreen warns on download. Enabling
signing later is one repository secret, `INNO_SIGN_COMMAND`, and no code
change — both build scripts take `--sign-command`, and `installer/Stash.iss`
has the `SignTool` block behind `#ifdef Sign`. Write it in Inno's form, with
`$f` for the file:

```
signtool.exe sign /fd sha256 /tr http://timestamp.digicert.com /td sha256 $f
```

The app is signed as well as the installer — a signed `Setup.exe` that lays
down an unsigned `Stash.exe` still trips SmartScreen when the app launches.

## Command line

The core (`stashlib/`) has no Qt in it and runs on its own — useful for
scripting, and it's how the search ranking gets tuned:

```
python.exe -m stashlib.cli scan
python.exe -m stashlib.cli search "air horn"
python.exe -m stashlib.cli search whoosh --kind audio --limit 10
python.exe -m stashlib.cli roots --add "D:\videos\overlays" --label Overlays
python.exe -m stashlib.cli tags
python.exe -m stashlib.normalize          # filename-normaliser self-test
```

## Layout

```
stash/
├── install.bat            one-time setup: deps + icon + shortcuts
├── run_panel.bat          double-click to launch
├── requirements.txt       what the app needs to run
├── requirements-build.txt PyInstaller, pinned (build only)
├── CHANGELOG.md           hand-written; release.py stamps the headings
├── .github/workflows/
│   ├── ci.yml             fast gate on every push
│   └── release.yml        tag -> build -> smoke test -> GitHub Release
├── installer/
│   └── Stash.iss          Inno Setup script -> Setup.exe with uninstaller
├── stashlib/              core: scan, index, search, thumbnails  (no Qt)
│   └── _version.py        the version, and the only copy of it
├── panel/                 the PySide6 window
│   └── selftest.py        does the frozen build actually work?
├── scripts/
│   ├── make_icon.py       draws panel/icon.ico
│   ├── install_shortcut.py  Desktop + Start Menu (--remove to undo)
│   ├── build_exe.py       standalone .exe via PyInstaller
│   ├── build_installer.py distributable Setup.exe via Inno Setup
│   ├── check_version.py   version is well formed / matches the tag
│   ├── release.py         bump, tag, push — CI does the rest
│   ├── ci/                helpers the workflows call
│   └── spike_drag.py      drag-into-Resolve regression harness
└── NOTES.md               measurements, gotchas, TODOs
```

## If something goes wrong

- **Nothing happens on double-click** — `run_panel.bat` uses `pythonw.exe`,
  which has no console. Check `%TEMP%\stash-panel.log`.
- **Empty grid** — click **＋** and add a folder, then **⟳**.
- **Drag does nothing** — if Resolve was started *as administrator* and the
  panel wasn't, Windows blocks the drag by design. Run both the same way.
- **`Ctrl+Shift+M` does nothing** — another app owns it; the status bar says so
  at startup. Everything else still works.
- **Rebuilding from scratch** — delete
  `%LOCALAPPDATA%\Stash\library\` and relaunch.
