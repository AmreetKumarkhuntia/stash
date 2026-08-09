"""Single source of truth for the product version.

Nothing else in the repo hard-codes it. It flows outward to:

  * ``stashlib.__version__``
  * the Windows VERSIONINFO resource on Stash.exe   (scripts/build_exe.py)
  * ``AppVersion`` in the Inno script               (scripts/build_installer.py)
  * the installer filename, Stash-Setup-X.Y.Z.exe
  * the git tag vX.Y.Z                              (scripts/release.py)

Deliberately import-free and on one line, so scripts/release.py can rewrite it
with a regex and CI can read it without importing Qt or anything else.

X.Y.Z only, no suffixes. Two consumers cannot cope with more: the Windows
VERSIONINFO resource needs four integers, and the Inno preprocessor has to
guess whether /DAppVersion=1.2 is a number or a string.
"""

__version__ = "1.3.0"
