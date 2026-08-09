"""Does the shipped binary actually work? — a smoke test for the frozen app.

Run it on the .exe, not on a checkout:

    Stash.exe --selftest [--selftest-log PATH]

Exit code 0 means every check passed, 1 means at least one failed. The shipped
build is --windowed, so it has no console and sys.stdout / sys.stderr are None:
the exit code and the log file are the only channels that exist. print() is a
silent no-op in that state (CPython returns early when sys.stdout is None), so
the calls below are harmless when frozen and useful when not.

The checks are not generic. Each one is something that has actually broken in
this project and was invisible in the source tree:

  * QtMultimedia lives in PySide6-Addons, not Essentials.
  * imageio_ffmpeg's ffmpeg.exe is data, not an import, so it only ships
    because build_exe.py adds it with --add-binary by hand.
  * style.qss only exists in the bundle because of --add-data.
  * sys.stderr is None in a windowed build, and probe.silence_native_stderr()
    touching it silently killed every audio waveform.

Nothing in here may raise. See the note in panel/__main__.py: an exception that
escapes to the PyInstaller bootloader becomes a modal dialog, which on an
unattended machine is a hang rather than a failure.
"""

from __future__ import annotations

import platform
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Callable


def _checks(resource: Callable[[str], Path]) -> list[tuple[str, Callable[[], str | None]]]:
    def qt_core() -> str:
        import PySide6
        from PySide6 import QtCore

        return f"PySide6 {PySide6.__version__}, Qt {QtCore.qVersion()}"

    def qt_widgets() -> None:
        from PySide6.QtGui import QIcon  # noqa: F401
        from PySide6.QtWidgets import QApplication, QMainWindow  # noqa: F401

    def qt_multimedia() -> None:
        # Addons, not Essentials — the single most likely thing to go missing.
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer  # noqa: F401
        from PySide6.QtMultimediaWidgets import QVideoWidget  # noqa: F401

    def ffmpeg() -> str:
        import imageio_ffmpeg

        exe = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if not exe.exists():
            raise FileNotFoundError(f"--add-binary did not ship it: {exe}")
        return f"{exe.name}, {exe.stat().st_size // 1024} KB"

    def media_stack() -> str:
        import numpy
        import soundfile
        from PIL import Image, ImageDraw  # noqa: F401

        return f"numpy {numpy.__version__}, libsndfile {soundfile.__libsndfile_version__}"

    def pywin32() -> None:
        import pythoncom  # noqa: F401
        import win32com.client  # noqa: F401

    def stylesheet() -> str:
        qss = resource("style.qss")
        if not qss.exists():
            raise FileNotFoundError(f"--add-data did not ship it: {qss}")
        return f"{qss.stat().st_size} bytes"

    def core() -> str:
        from stashlib import __version__, normalize

        if normalize._selftest() != 0:
            raise AssertionError("the golden corpus in stashlib.normalize failed")
        return f"Stash {__version__}, {len(normalize.CORPUS)} corpus cases"

    def panel_modules() -> None:
        import panel.app  # noqa: F401
        import panel.debug  # noqa: F401
        import panel.delegate  # noqa: F401
        import panel.filters  # noqa: F401
        import panel.hotkey  # noqa: F401
        import panel.model  # noqa: F401
        import panel.preview  # noqa: F401
        import panel.results_view  # noqa: F401
        import panel.roots_dialog  # noqa: F401
        import panel.theme  # noqa: F401
        import panel.thumb_loader  # noqa: F401
        import panel.workers  # noqa: F401

    def waveform() -> str:
        """The exact combination that silently killed audio thumbnails.

        soundfile through probe.silence_native_stderr() with sys.stderr None,
        then PIL. Rendering one short tone exercises the whole path end to end
        in the real windowed binary, which is where the bug lived and where
        running it from source could never have found it.
        """
        import numpy as np
        import soundfile

        from stashlib import thumbs
        from stashlib.model import MediaItem

        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "tone.wav"
            tone = (np.sin(np.linspace(0.0, 220 * 2 * np.pi, 8000)) * 0.5).astype("float32")
            soundfile.write(str(wav), tone, 8000)
            stat = wav.stat()
            item = MediaItem(
                path=str(wav), root=tmp, root_label="selftest", rel_dir="",
                stem="tone", norm="tone", ext=".wav", kind="audio",
                size=stat.st_size, mtime=stat.st_mtime,
            )
            png = Path(tmp) / "wave.png"
            if not thumbs._render_waveform(item, png):
                raise AssertionError("_render_waveform returned False")
            if png.stat().st_size == 0:
                raise AssertionError("_render_waveform wrote an empty PNG")
            written = png.stat().st_size
        return f"220 Hz tone -> {written} byte waveform PNG"

    return [
        ("PySide6 core", qt_core),
        ("PySide6 widgets", qt_widgets),
        ("PySide6 multimedia (Addons)", qt_multimedia),
        ("imageio_ffmpeg binary", ffmpeg),
        ("numpy / Pillow / soundfile", media_stack),
        ("pywin32", pywin32),
        ("bundled style.qss", stylesheet),
        ("stashlib core", core),
        ("panel modules", panel_modules),
        ("waveform render (windowed stderr path)", waveform),
    ]


def _log_path(argv: list[str]) -> Path | None:
    if "--selftest-log" in argv:
        index = argv.index("--selftest-log") + 1
        if index < len(argv):
            return Path(argv[index])
    try:
        from stashlib import config

        return config.cache_dir() / "selftest.log"
    except Exception:
        return None


def run(argv: list[str], resource: Callable[[str], Path]) -> int:
    checks = _checks(resource)
    lines = [
        f"Stash selftest — {platform.platform()}",
        f"executable = {sys.executable}",
        f"frozen = {getattr(sys, 'frozen', False)}  "
        f"stdout = {'None' if sys.stdout is None else 'open'}  "
        f"stderr = {'None' if sys.stderr is None else 'open'}",
        "",
    ]
    failures = 0
    for name, check in checks:
        try:
            detail = check()
        except BaseException:  # noqa: BLE001 — nothing may escape, see the module docstring
            failures += 1
            lines.append(f"FAIL  {name}")
            lines += ["        " + line for line in traceback.format_exc().splitlines()]
        else:
            lines.append(f"ok    {name}" + (f"  ({detail})" if detail else ""))

    lines += ["", f"{len(checks) - failures}/{len(checks)} checks passed"]
    report = "\n".join(lines)

    log = _log_path(argv)
    if log is not None:
        try:
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(report + "\n", encoding="utf-8")
        except OSError:
            pass
    print(report)  # a no-op when sys.stdout is None, which is the shipped case
    return 1 if failures else 0
