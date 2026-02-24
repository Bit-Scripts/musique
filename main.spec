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
    ('data/edit-clear.svg','data')
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
    a.binaries,
    a.datas,
    [],
    name='BIT SCRIPTS - Musique',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True
)
