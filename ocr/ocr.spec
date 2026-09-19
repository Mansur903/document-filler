from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata

# PyInstaller configuration for packaging the OCR worker and its dependencies.

ocr_directory = Path(SPECPATH)
datas = []
binaries = []
hidden_imports = []

for package_name in ("paddle", "paddleocr", "paddlex"):
    package_datas, package_binaries, package_hidden_imports = collect_all(package_name)
    datas += package_datas
    binaries += package_binaries
    hidden_imports += package_hidden_imports

for distribution_name in (
    "imagesize",
    "opencv-contrib-python",
    "pyclipper",
    "pypdfium2",
    "python-bidi",
    "shapely",
):
    datas += copy_metadata(distribution_name)

analysis = Analysis(
    [str(ocr_directory / "recognize_passport.py")],
    pathex=[str(ocr_directory)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
python_archive = PYZ(analysis.pure)

executable = EXE(
    python_archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="ocr",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

collection = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ocr",
)
