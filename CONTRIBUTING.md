# Contributing

Conventions for this repo: how commits are written, and how a release is cut.

## Commit messages

```
type(scope): short description

Longer description: what changed and, more importantly, why. Wrap at 72
columns. Explain the reasoning a diff cannot show — the constraint you were
working around, the approach you rejected, the bug this prevents.
```

**Types** — `feat` for new capability, `fix` for a bug, `chore` for everything
else (docs, dependencies, tooling, CI). Use `docs`, `refactor`, `test` or `ci`
instead of `chore` if you want the extra precision; the shape is the same.

**Scope** is the area touched, lowercase, one word:

| Scope | Covers |
|---|---|
| `panel` | the PySide6 window — views, delegates, preview, hotkey |
| `stashlib` | scan, index, search, normalise, thumbnails, probe |
| `installer` | `Stash.iss`, the build scripts |
| `release` | versioning, tagging, `release.py` |
| `ci` | the GitHub Actions workflows |
| `docs` | README, NOTES, this file |

**Rules that matter:**

- Short description in the **imperative** — "add", not "added" or "adds" —
  under ~70 characters, no trailing full stop.
- Blank line between the subject and the body. Git treats the first line as
  the subject; without the blank line the whole thing becomes one paragraph.
- The body is where the value is. A commit that says *what* is a worse version
  of the diff; a commit that says *why* is the only record of the reasoning.
- Note bugs found on the way, even small ones. They are the hardest thing to
  rediscover later.

Examples from this repo:

```
feat(release): publish the installer to GitHub Releases on a tag

Building a release was a manual job on one machine, and there was nowhere
for anyone to download Stash from. Now `release.py --bump minor` tags and
pushes; Actions builds on a clean runner and publishes. Nothing is ever
uploaded from a developer machine.
```

```
fix(installer): pick the built installer by exact name, not sorted(glob)[-1]

sorted() is lexicographic, so a stale Stash-Setup-1.9.0.exe in the output
folder would have beaten the Stash-Setup-1.10.0.exe just built. Using the
exact expected filename also proves /DAppVersion reached the .iss instead
of silently falling back to the literal in the script.
```

## Releasing

### The version lives in one place

`stashlib/_version.py`. Everything else derives from it — Inno's `AppVersion`,
the installer filename, the exe's file properties, the "Installed apps" entry,
and the git tag. Never edit it by hand; `release.py` owns it.

`scripts/check_version.py --expect-tag vX.Y.Z` is what makes it impossible to
publish `Stash-Setup-1.0.0.exe` under the tag `v1.2.3`. It is the first step of
the release job, so a mismatch costs two seconds instead of twelve minutes.

### Cutting a release

1. **Write the changelog first.** Put what changed under `## Unreleased` in
   `CHANGELOG.md`. `release.py` refuses to release with that section empty —
   that text becomes the release's changelog entry.

2. **Dry run, if anything under `scripts/` or `installer/` changed.**
   Actions → Release → Run workflow. Started from a branch it is *always* a dry
   run: the whole build, both selftests and the install/uninstall round trip,
   publishing nothing. The installer is attached to the run as an artifact.

3. **Cut it.**

   ```
   python scripts/release.py --bump patch     # or minor / major, or 1.2.3
   ```

   `--dry-run` checks everything and writes nothing. `--no-push` commits and
   tags locally so you can inspect before pushing.

   That bumps `_version.py`, stamps the `CHANGELOG.md` heading with today's
   date, commits as `Release vX.Y.Z`, tags, and runs
   `git push --atomic origin main vX.Y.Z` — atomic so a tag never arrives
   without its commit.

4. **The tag push is the trigger.** Actions builds the app and installer, runs
   `Stash.exe --selftest` on the unpacked build, silently installs it, runs the
   selftest again on the *installed* copy, uninstalls, then publishes
   `Stash-Setup-X.Y.Z.exe` and `SHA256SUMS.txt` to a new GitHub Release. Any
   step failing means nothing is published.

Choosing the bump: `feat` commits since the last tag mean `minor`, `fix`-only
means `patch`, a breaking change to the library index or config layout means
`major`.

### Do not create releases in the browser

It looks like it should work — the UI creates a tag, and that does trigger the
workflow. But it leaves `stashlib/_version.py` untouched, so the tag check
fails in two seconds, and even past that `gh release create` collides with the
release the browser already made. The result is a public release with **no
installer attached** next to a red build.

Editing the notes in the browser *afterwards* is fine and expected — CI writes
generated notes, and they are yours to rewrite.

### When something goes wrong

| Situation | Fix |
|---|---|
| Build failed after tagging | `git push origin :refs/tags/vX.Y.Z && git tag -d vX.Y.Z`, fix, tag again |
| Build passed, publish flaked | Re-run the workflow **from the tag ref** — do not re-tag |
| Tagged the wrong version | Delete the tag as above; `_version.py` and the tag must always agree |

### Signing

Releases are unsigned, so SmartScreen warns on download. Enabling it later is
one repository secret, `INNO_SIGN_COMMAND`, and no code change — both build
scripts take `--sign-command` (honouring Inno's `$f` placeholder) and
`installer/Stash.iss` has the `SignTool` block behind `#ifdef Sign`. The app is
signed as well as the installer: a signed `Setup.exe` that lays down an
unsigned `Stash.exe` still trips SmartScreen when the app launches.
