# -*- mode: python ; coding: utf-8 -*-
"""macOS 独立可执行包构建配置（PyInstaller onedir）。

用法（在项目根目录）:
  .venv/bin/pyinstaller packaging/milodi.spec --noconfirm --clean
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

root = Path(SPECPATH).parent
entry = root / "packaging" / "milodi_entry.py"

datas = [
    (str(root / "web" / "static"), "milodi/web/static"),
]
binaries = []
hiddenimports = [
    "milodi",
    "milodi.cli",
    "milodi.extract",
    "milodi.export",
    "milodi.h300",
    "milodi.notes",
    "milodi.playback",
    "milodi.preprocess",
    "milodi.web.app",
    "basic_pitch",
    "basic_pitch.inference",
    "basic_pitch.constants",
    "basic_pitch.note_creation",
    "basic_pitch.layers.signal",
    "basic_pitch.layers.nnaudio",
    "basic_pitch.layers.math",
    "librosa",
    "librosa.core",
    "librosa.feature",
    "librosa.util",
    "pretty_midi",
    "soundfile",
    "sounddevice",
    "scipy.signal",
    "resampy",
    "audioread",
    "sklearn",
    "sklearn.utils",
    "numba",
    "flask",
]

for pkg in (
    "basic_pitch",
    "librosa",
    "tensorflow",
    "pretty_midi",
    "soundfile",
    "sklearn",
    "numba",
    "resampy",
    "flask",
):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception:
        pass

# basic_pitch 内置模型（TF / CoreML / TFLite / ONNX）
import basic_pitch

bp_models = Path(basic_pitch.__file__).parent / "saved_models"
datas.append((str(bp_models), "basic_pitch/saved_models"))

a = Analysis(
    [str(entry)],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="milodi",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="milodi",
)
