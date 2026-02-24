# -*- mode: python ; coding: utf-8 -*-


import os
data_files = [
    ('data/add-one-hover.svg', 'data'),
    ('data/add-one.svg', 'data'),
    ('data/close-one-hover.svg', 'data'),
    ('data/close-one.svg', 'data'),
    ('data/Music bot.png','data'),
    ('data/reduce-one-hover.svg','data'),
    ('data/reduce-one.svg','data'),
    ('data/refresh-1.svg','data'),
    ('data/refresh.svg','data'),
    ('data/shuffle.svg','data'),
    ('data/volume-down.svg','data'),
    ('data/volume-mute.svg','data'),
    ('data/volume-notice.svg','data'),
    ('data/volume-up.svg','data'),
    ('data/edit-add.svg','data'),
    ('data/edit-clear.svg','data'),
    ('data/Music bot.icns','data')
]

if os.path.exists('.env'):
    data_files.append(('.env', '.'))

a = Analysis(
    ['main.py'],
    pathex=['core', 'ui'],
    binaries=[],
    datas=data_files,
    hiddenimports=[
        'PIL', 'PIL.Image',
        'pydub', 'PyQt5', 'numpy', 'qasync', 'mutagen', 'pyimgur', 'dotenv', 'pyqtgraph', 'pypresence'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BIT_SCRIPTS_-_Musique',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='data/Music bot.icns',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],

    name='BIT_SCRIPTS_-_Musique',
)
app = BUNDLE(
    coll,
    name='BIT_SCRIPTS_-_Musique.app',
    icon='data/Music bot.icns',
    bundle_identifier=None,
)

## Make app bundle double-clickable
import plistlib
from pathlib import Path
app_path = Path(app.name)

# read Info.plist
with open(app_path / 'Contents/Info.plist', 'rb') as f:
    pl = plistlib.load(f)

# write Info.plist
with open(app_path / 'Contents/Info.plist', 'wb') as f:
    pl['CFBundleExecutable'] = 'wrapper'
    plistlib.dump(pl, f)

# write new wrapper script
shell_script = """#!/bin/bash
dir=$(dirname $0)
open file://${dir}/%s  &> /dev/null &""" % app.appname
with open(app_path / 'Contents/MacOS/wrapper', 'w') as f:
    f.write(shell_script)

# make it executable
(app_path  / 'Contents/MacOS/wrapper').chmod(0o755)