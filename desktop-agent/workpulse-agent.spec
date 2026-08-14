# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for a later Windows executable. Do not bundle .env or device_secret.
# Build from desktop-agent/: pyinstaller workpulse-agent.spec

from PyInstaller.utils.hooks import collect_submodules

hidden = collect_submodules("app")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[".env", "device_secret"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="WorkPulseAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
