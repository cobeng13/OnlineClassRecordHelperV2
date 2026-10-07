# Validation status

Checked on Windows 11 x64, using Python 3.12.14 and Python 3.11.0, on October 7, 2026. The declared minimum Python version is 3.11.

## Passed

- 24 automated tests: parsing and Unicode, all four single-column advance keys, row-major ordering, multi-column counts 1–5, column clamping, uneven rows, blank handling, no extra final Enter, test mode with zero keyboard events, stop before/during/after entry, countdown cancellation, interrupted delays, and inter-column cancellation.
- Qt UI checks: default settings, clipboard import, preview, overlapping-start prevention, disabled controls during runs, error recovery, permission blocking, and test mode without permissions.
- Mocked macOS permissions: Accessibility, Input Monitoring, and event-post access must all pass before live execution.
- Mocked native integration: Unicode dispatch, cancellation between characters, key press/release, shortcut mapping, and listener startup failure.
- Source startup smoke check: offscreen preview and test run, native-module imports, and instance-lock exclusion/reacquisition; exit code 0.
- Windows standalone bundle built and its no-keyboard smoke check passed, exit code 0. The specification excludes conflicting ICU DLLs from the build runtime so Qt uses the Windows ICU API.
- Dependency consistency: `pip check` passed.
- Python 3.11 verification: all 24 tests passed, pinned dependencies installed successfully, `pip check` passed, and the source no-keyboard startup smoke check exited 0. Python 3.11 packaging on each target platform is covered by the CI matrix; a local 3.11 bundle was not built in this compatibility update.
- Offscreen UI layout inspected using an explicitly loaded Windows font; controls and guidance are legible with no clipping at the default window size.

Windows sandbox restrictions prevent Qt instance-lock operations and automatic font discovery in the offscreen renderer. The source smoke check ran successfully outside that sandbox; the layout check loaded Segoe UI explicitly. Neither diagnostic emitted keyboard input.

## Remaining release checks

- Build and test the Intel and Apple Silicon macOS bundles on their native platforms. The workflow is configured but has not run here; actual macOS permission grants, shortcuts, and macOS 13 compatibility remain unverified.
- Interactive Windows/macOS checks: focus handoff, F9/F10/Esc while the browser is focused, stop during live typing, and closing during a live run.
- The user will manually test the actual class-record website. With a disposable full-length student grid and 2–3 columns, verify every entered value, blank preservation, the Right/Up column transition, and Enter remaining on the final student row. Also test F10/Esc mid-run and confirm no further navigation occurs. This live check has not been performed by the agent.
- Validate on Windows 10 and the minimum supported macOS release before claiming coverage for those OS versions.
- Public signing/notarization requires separate credentials and release work.

The automated smoke check intentionally never emits real keystrokes. Passing it confirms packaging/startup and dry-run behavior, not website compatibility or OS-level keyboard delivery.
