# Run from the repository root: python -m PyInstaller packaging/helper.spec --noconfirm
import sys
import importlib.metadata
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH).parent
hidden = collect_submodules('pynput')
license_data = [(str(root / 'THIRD_PARTY_NOTICES.md'), '.')]
license_data += [(str(root / name), 'docs') for name in ('README.md', 'VALIDATION.md')]
python_license = Path(sys.base_prefix) / 'LICENSE.txt'
if python_license.is_file():
    license_data.append((str(python_license), 'licenses/Python'))
for distribution in importlib.metadata.distributions():
    name = distribution.metadata.get('Name', '')
    if name.lower().startswith(('pyside6', 'shiboken6', 'pynput', 'six', 'pyobjc', 'pyinstaller')):
        for file in distribution.files or []:
            if any(word in str(file).lower() for word in ('license', 'copying')):
                source = Path(distribution.locate_file(file))
                if source.is_file():
                    license_data.append((str(source), str(Path('licenses') / name / file.parent)))
a = Analysis([str(root / 'run_app.py')], pathex=[str(root)],
             binaries=[], datas=license_data, hiddenimports=hidden,
             hookspath=[], runtime_hooks=[], excludes=['tkinter'], noarchive=False)
if sys.platform == 'win32':
    # Qt uses Windows' unversioned ICU API. Conda/bundled Python can supply a
    # different icuuc.dll whose versioned exports are incompatible with Qt.
    # Let the Windows loader resolve these OS components from System32.
    a.binaries = [entry for entry in a.binaries
                  if Path(entry[0]).name.lower() not in {'icuuc.dll', 'icuin.dll', 'icudt78.dll'}]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name='Online Class Record Helper', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, target_arch=None, codesign_identity=None, entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False,
               name='Online Class Record Helper')
if sys.platform == 'darwin':
    app = BUNDLE(coll, name='Online Class Record Helper.app',
                 bundle_identifier='org.onlineclassrecordhelper.desktop',
                 info_plist={
                     'CFBundleShortVersionString': '1.0.0',
                     'LSMinimumSystemVersion': '13.0',
                     'NSHighResolutionCapable': True,
                     'NSInputMonitoringUsageDescription': 'F9 starts entry; F10 and Escape stop entry.',
                 })
