# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('src', 'src'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'google.generativeai',
        'dotenv',
        'pandas',
        'numpy',
        'openpyxl',
        'xlsxwriter',
        'fastapi',
        'uvicorn',
        'werkzeug',
        'flask',
        'flask_wtf',
        'requests',
        'python_dotenv',
        'python_magic',
        'APScheduler',
        'pytest',
    ],
    hookspath=[],
    hooksconfig={},
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AIDN',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/assets/favicon/favicon.ico',
)
