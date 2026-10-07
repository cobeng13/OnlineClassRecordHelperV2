# Third-party components

The app uses dynamically loaded Qt/PySide6 libraries, distributed under the available LGPLv3/GPLv3/commercial terms; this build uses the LGPL route. Keep Qt libraries separate and replaceable in the bundle. Preserve the collected license files when redistributing. Qt/PySide6 source and licensing information: https://code.qt.io/pyside/pyside-setup.git/ and https://www.qt.io/licensing/open-source-lgpl-obligations.

pynput is LGPLv3: https://github.com/moses-palmer/pynput.

shiboken6 follows its included LGPL/GPL/commercial notices. six is MIT licensed. macOS builds also include PyObjC components under the MIT license: https://github.com/ronaldoussoren/pyobjc.

PyInstaller's bootloader is GPLv2 with an exception allowing distribution of bundled applications: https://pyinstaller.org/en/stable/license.html. Python's license information: https://docs.python.org/3/license.html.

The packaging specification collects installed package license files into `_internal/licenses` and includes this notice. Consult those files for the exact terms applying to a given build.
