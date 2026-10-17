from __future__ import annotations

from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import sys
import traceback
from typing import Any, cast

from mrz_parser import parse_passport_data
from ocr_config import (
    create_pipeline_settings,
    get_primary_profile,
    get_required_model_names,
)
from passport_data_model import (
    DocumentType,
    OcrTextBlock,
    PassportData,
    ResidencePermitData,
)
from residence_permit_parser import (
    has_residence_permit_anchors,
    parse_residence_permit_data,
)


RESULT_PREFIX = "OCR_RESULT:"
DOCUMENT_TYPES: tuple[DocumentType, ...] = ("passport", "uaeResidencePermit")
SUPPORTED_EXTENSIONS = {".jpeg", ".jpg", ".pdf", ".png"}


def recognize_document(
    document_file_path: Path, document_type: DocumentType
) -> PassportData | ResidencePermitData:
    os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "bos")
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

    with redirect_stdout(sys.stderr):
        from paddleocr import PaddleOCR

        profile = get_primary_profile(document_type)
        model_root = _get_bundled_model_root()
        ocr = PaddleOCR(**create_pipeline_settings(profile, model_root))
        results = ocr.predict(str(document_file_path))

    return _select_document_page(results, document_type)


def _select_document_page(
    results: Any, document_type: DocumentType
) -> PassportData | ResidencePermitData:
    if document_type == "passport":
        return _select_passport_page(results)

    return _select_residence_permit_page(results)


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


def _select_residence_permit_page(results: Any) -> ResidencePermitData:
    has_pages = False

    for result in results:
        has_pages = True
        ocr_blocks = _extract_text_blocks(result)

        if has_residence_permit_anchors(ocr_blocks):
            return parse_residence_permit_data(ocr_blocks)

    if not has_pages:
        raise ValueError("OCR returned no document pages.")

    return parse_residence_permit_data([])


def _extract_text_blocks(result: Any) -> list[OcrTextBlock]:
    blocks: list[OcrTextBlock] = []
    recognized_texts = result.get("rec_texts", [])
    recognized_boxes = result.get("rec_boxes")

    for index, text in enumerate(recognized_texts):
        recognized_text = str(text).strip()

        if not recognized_text:
            continue

        raw_box = (
            recognized_boxes[index]
            if recognized_boxes is not None
            else (0, index, 0, index)
        )
        box = tuple(int(value) for value in raw_box[:4])
        blocks.append({"box": box, "text": recognized_text})

    return blocks


def _get_bundled_model_root() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None

    model_root = Path(sys.executable).resolve().parent / "models"

    if not all(
        (model_root / model_name).is_dir()
        for model_name in get_required_model_names()
    ):
        raise FileNotFoundError("Required OCR models are missing.")

    return model_root


def _validate_input_path(raw_path: str) -> Path:
    input_path = Path(raw_path).resolve(strict=True)

    if not input_path.is_file():
        raise ValueError("The OCR input must be a file.")

    if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only JPG, JPEG, PNG, and PDF files are supported.")

    return input_path


def _validate_document_type(raw_document_type: str) -> DocumentType:
    if raw_document_type not in DOCUMENT_TYPES:
        raise ValueError("The requested document type is not supported.")

    return cast(DocumentType, raw_document_type)


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: recognize_passport.py <document-type> <document-file-path>",
            file=sys.stderr,
        )
        return 2

    try:
        document_type = _validate_document_type(sys.argv[1])
        document_data = recognize_document(
            _validate_input_path(sys.argv[2]), document_type
        )
    except Exception as error:
        traceback.print_exc(file=sys.stderr)
        print(f"OCR failed: {error}", file=sys.stderr)
        return 1

    print(f"{RESULT_PREFIX}{json.dumps(document_data)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
