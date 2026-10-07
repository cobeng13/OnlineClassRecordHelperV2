# Online Class Record Helper

A Python desktop replacement for the old AutoHotkey **V2** helper, using PySide6 and pynput. It transfers copied spreadsheet cells to the currently focused web grid by typing text and navigation keys. The old AHK source is untouched.

## Using the app

1. Open **Online Class Record Helper**.
2. Copy cells from Excel (or any spreadsheet), then paste into the data area or click **From Clipboard**.
3. Review **Cell preview** and **Action preview**. The latter lists every planned text/navigation action in order.
4. Configure the delays and navigation. Defaults match V2: 3-second initial delay, 250-ms key delay, Enter, skip blanks on, single-column mode.
5. Try **Test mode** first. It runs the countdown/progress without sending any keyboard input, including navigation.
6. Click **Start** or press **F9**, then click the **first destination cell** before the countdown ends. The always-on-top helper reports progress without taking focus.
7. Press **F10** or **Esc** to stop, including during the countdown. On Mac, F9/F10 may require **Fn**. Start/Stop buttons are also available.

**Single-column mode:** flattens pasted cells row by row. Each cell advances using the selected Enter, Tab, Down, or Right key.

**Multi-column mode:** fills down using Enter after every cell, then sends Right and `row count − 1` Up keys before filling the next column. Choose 1–5 columns; the app clamps this to the data width. Missing cells in uneven rows count as blanks. **Your pasted block must end at the website's last student row, where Enter stays on that row.** This preserves V2's navigation; partial blocks are not supported.

Skip blanks advances without typing. Turning it off sends empty text and advances; neither setting clears an existing grade. Values are trimmed, tabs delimit cells, and newlines delimit rows. Quoted cells with embedded tabs/newlines are not supported, matching V2. There is no extra final Enter.

The key delay follows each text and navigation action (so a populated cell normally takes twice that delay). Stop cancels remaining actions; it cannot undo already-entered values. Keep the destination focused during a live run. This app does not inspect the page or confirm that the website saved grades.

Pasted data stays in memory and is not saved to disk, settings, or logs. Closing the app cancels the run and shuts down shortcuts. Only one copy runs per user session.

## Windows standalone

Target: Windows 10/11 x64. Extract the complete Windows bundle and open `Online Class Record Helper.exe`. Keep its `_internal` folder beside the executable. No Python installation is required. The executable is not publicly signed.

## macOS standalone

Target: macOS 13+, with separate **Apple Silicon (M-series)** and **Intel** builds. Unzip the matching bundle, move `Online Class Record Helper.app` to Applications, and open it.

In **System Settings → Privacy & Security**, enable the app under **Accessibility** and **Input Monitoring**. If necessary, add it using the + button. Quit and reopen the app after changing permissions. **Recheck access** refreshes status; live entry is blocked until access is available, while test mode works without it. Source runs may need permissions for Terminal/Python instead.

Initial builds are ad-hoc signed by the packager, not Developer ID signed or notarized. macOS may require approval through **Privacy & Security → Open Anyway** for a trusted downloaded build. Replacing/rebuilding an app may require granting access again. Do not distribute it as a notarized release without the corresponding Apple signing process.

Keyboard permission behavior: [pynput platform limitations](https://pynput.readthedocs.io/en/latest/limitations.html).

## Development

Use 64-bit Python 3.11, 3.12, or 3.13. From the repository root:

`requirements.txt` pins the main packages and uses `packaging/constraints.txt` to pin their build/runtime dependencies on Windows and macOS. CI tests and packages each platform with Python 3.11 and 3.12.

```powershell
# Windows
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_app.py
```

```sh
# macOS
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run_app.py
```

On macOS, use `python3.12` or `python3.13` in the environment-creation command to choose another installed version. Create a fresh virtual environment when changing Python versions; Windows environments cannot be copied to macOS.

Core tests need only Python. UI tests require PySide6 and run offscreen with mocked keyboard access; they never type into other apps.

```sh
python -m unittest discover -s tests -v
```

Architecture: `core.py` parses and plans immutable actions and executes them with interruptible waits; `desktop.py` owns native typing, permissions, and shortcuts; `app.py` owns preview/UI and marshals worker updates through Qt signals. No website credentials or browser extension is needed.

## Build

From the root, with the virtual environment's Python:

```sh
python -m PyInstaller packaging/helper.spec --noconfirm
```

Windows output: `dist/Online Class Record Helper/`. macOS output: `dist/Online Class Record Helper.app`. Build each architecture using a matching Python installation on that platform. [PyInstaller builds are platform-specific](https://pyinstaller.org/en/stable/usage.html).

`.github/workflows/build.yml` supplies Windows x64, macOS Intel, and macOS Apple Silicon build jobs for Python 3.11 and 3.12. It runs on pushes to `main`, version tags, pull requests, or manual dispatch. It uploads build artifacts, not public releases. Mac ZIPs preserve executable permissions. Core/UI tests run before packaging; interactive testing remains necessary.

The packaged executable accepts `--smoke-test`: an offscreen startup, synthetic-data preview/test run, native-module import, and instance-lock check. Exit code 0 means success. It emits no keyboard events. This automated check also runs in the build workflow.

See [VALIDATION.md](VALIDATION.md) for verification results and remaining release checks, and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for dependency notices.
