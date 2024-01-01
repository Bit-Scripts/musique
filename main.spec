# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('data/add-one-hover.svg', 'data'),
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
    ('.env','.')
    ],
    hiddenimports=[],
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
