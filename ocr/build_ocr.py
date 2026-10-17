"""Builds the standalone OCR executable and copies its local models."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

from ocr_config import (
    OCR_MODEL_PROFILES,
    create_pipeline_settings,
    get_required_model_names,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUILD_ROOT = PROJECT_ROOT / ".ocr-build"
OCR_OUTPUT = BUILD_ROOT / "ocr"
MODEL_CACHE = Path.home() / ".paddlex" / "official_models"


def main() -> int:
    _ensure_models_are_downloaded()
    _build_executable()
    _copy_models()
    print(f"OCR runtime created at {OCR_OUTPUT}")
    return 0


def _ensure_models_are_downloaded() -> None:
    if _models_exist():
        return

    os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "bos")
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

    from paddleocr import PaddleOCR

    for profile in OCR_MODEL_PROFILES:
        PaddleOCR(**create_pipeline_settings(profile))

    if not _models_exist():
        raise FileNotFoundError(f"OCR models were not downloaded to {MODEL_CACHE}")


def _models_exist(model_cache: Path = MODEL_CACHE) -> bool:
    return all(
        (model_cache / model_name).is_dir()
        for model_name in get_required_model_names()
    )


def _build_executable() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(BUILD_ROOT),
            "--workpath",
            str(BUILD_ROOT / "work"),
            str(Path(__file__).resolve().parent / "ocr.spec"),
        ],
        cwd=PROJECT_ROOT,
        check=True,
    )


def _copy_models(
    model_cache: Path = MODEL_CACHE, ocr_output: Path = OCR_OUTPUT
) -> None:
    destination = ocr_output / "models"

    if destination.exists():
        shutil.rmtree(destination)

    destination.mkdir(parents=True)

    for model_name in get_required_model_names():
        shutil.copytree(model_cache / model_name, destination / model_name)


if __name__ == "__main__":
    raise SystemExit(main())
