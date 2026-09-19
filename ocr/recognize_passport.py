from __future__ import annotations

from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import sys
import traceback
from typing import Any

from mrz_parser import parse_passport_data
from passport_data_model import OcrTextBlock, PassportData


RESULT_PREFIX = "OCR_RESULT:"
SUPPORTED_EXTENSIONS = {".jpeg", ".jpg", ".pdf"}
DETECTION_MODEL_NAME = "PP-OCRv6_tiny_det"
RECOGNITION_MODEL_NAME = "cyrillic_PP-OCRv5_mobile_rec"


def recognize_passport(passport_file_path: Path) -> PassportData:
    os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "bos")
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

    with redirect_stdout(sys.stderr):
        from paddleocr import PaddleOCR

        model_root = _get_bundled_model_root()
        model_settings = (
            {
                "text_detection_model_name": DETECTION_MODEL_NAME,
                "text_detection_model_dir": str(model_root / DETECTION_MODEL_NAME),
                "text_recognition_model_name": RECOGNITION_MODEL_NAME,
                "text_recognition_model_dir": str(model_root / RECOGNITION_MODEL_NAME),
            }
            if model_root
            else {
                "text_detection_model_name": DETECTION_MODEL_NAME,
                "text_recognition_model_name": RECOGNITION_MODEL_NAME,
            }
        )
        ocr = PaddleOCR(
            device="cpu",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            **model_settings,
        )
        results = ocr.predict(str(passport_file_path))

    return _select_passport_page(results)


def _select_passport_page(results: Any) -> PassportData:
    has_pages = False

    for result in results:
        has_pages = True
        passport_data = parse_passport_data(_extract_text_blocks(result))

        if passport_data["issuedByCountry"] == "RUS":
            return passport_data

    if not has_pages:
        raise ValueError("OCR returned no document pages.")

    return parse_passport_data([])


def _extract_text_blocks(result: Any) -> list[OcrTextBlock]:
    blocks: list[OcrTextBlock] = []
    recognized_texts = result.get("rec_texts", [])
    recognized_boxes = result.get("rec_boxes")

    for index, text in enumerate(recognized_texts):
        recognized_text = str(text).strip()

        if not recognized_text:
            continue

        raw_box = recognized_boxes[index] if recognized_boxes is not None else (0, index, 0, index)
        box = tuple(int(value) for value in raw_box[:4])
        blocks.append({"box": box, "text": recognized_text})

    return blocks


def _get_bundled_model_root() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None

    model_root = Path(sys.executable).resolve().parent / "models"
    required_models = (DETECTION_MODEL_NAME, RECOGNITION_MODEL_NAME)

    if not all((model_root / model_name).is_dir() for model_name in required_models):
        raise FileNotFoundError(f"OCR models are missing from {model_root}")

    return model_root


def _validate_input_path(raw_path: str) -> Path:
    input_path = Path(raw_path).resolve(strict=True)

    if not input_path.is_file():
        raise ValueError("The OCR input must be a file.")

    if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only JPG, JPEG, and PDF files are supported.")

    return input_path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: recognize_passport.py <passport-file-path>", file=sys.stderr)
        return 2

    try:
        passport_data = recognize_passport(_validate_input_path(sys.argv[1]))
    except Exception as error:
        traceback.print_exc(file=sys.stderr)
        print(f"OCR failed: {error}", file=sys.stderr)
        return 1

    print(f"{RESULT_PREFIX}{json.dumps(passport_data)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
