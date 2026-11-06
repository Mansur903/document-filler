from __future__ import annotations

from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import re
import sys
import traceback
from typing import Any, cast

from certificate_parser import merge_birth_certificate_pages, merge_marriage_certificate_pages
from internal_passport_parser import merge_internal_passport_pages, page_anchor_groups
from mrz_parser import parse_passport_data
from ocr_config import (
    create_pipeline_settings,
    get_primary_profile,
    get_required_model_names,
)
from passport_data_model import (
    BirthCertificateData,
    DocumentType,
    InternalPassportData,
    MarriageCertificateData,
    OcrTextBlock,
    PassportData,
    ResidencePermitData,
)
from residence_permit_parser import (
    has_residence_permit_anchors,
    parse_residence_permit_data,
)


RESULT_PREFIX = "OCR_RESULT:"
DOCUMENT_TYPES: tuple[DocumentType, ...] = (
    "passport",
    "russianBirthCertificate",
    "russianInternalPassport",
    "russianMarriageCertificate",
    "uaeResidencePermit",
)
SUPPORTED_EXTENSIONS = {".jpeg", ".jpg", ".pdf", ".png"}


def recognize_document(
    document_file_path: Path, document_type: DocumentType
) -> PassportData | InternalPassportData | ResidencePermitData | BirthCertificateData | MarriageCertificateData:
    os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "bos")
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

    with redirect_stdout(sys.stderr):
        from paddleocr import PaddleOCR

        profile = get_primary_profile(document_type)
        model_root = _get_bundled_model_root()
        ocr = PaddleOCR(**create_pipeline_settings(profile, model_root))
        results = (
            _predict_internal_pdf_pages(ocr, document_file_path)
            if document_type == "russianInternalPassport"
            and document_file_path.suffix.lower() == ".pdf"
            else list(ocr.predict(str(document_file_path)))
        )

        if document_type == "russianInternalPassport":
            pages = [_extract_text_blocks(result) for result in results]
            parsed = merge_internal_passport_pages(pages)
            if parsed["internalPassportNumber"] is None:
                supplemental = _read_rotated_side_numbers(
                    ocr, document_file_path, pages
                )
                if supplemental:
                    return merge_internal_passport_pages(pages, supplemental)

    parsed = _select_document_page(results, document_type)
    if document_type == "russianBirthCertificate" and document_file_path.suffix.lower() != ".pdf":
        with redirect_stdout(sys.stderr):
            birth = _retry_birth_missing_names(ocr, document_file_path, results, cast(BirthCertificateData, parsed))
            return _retry_birth_mother_surname(ocr, document_file_path, results, birth)
    return parsed


NAME_LOOKALIKES = str.maketrans({
    "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "K": "К", "M": "М",
    "O": "О", "P": "Р", "T": "Т", "X": "Х", "Y": "У",
    "a": "а", "c": "с", "e": "е", "n": "н", "o": "о", "p": "р", "r": "г", "x": "х", "y": "у",
})


def _retry_birth_missing_names(
    ocr: Any, document_file_path: Path, results: list[Any], parsed: BirthCertificateData
) -> BirthCertificateData:
    """Re-reads mixed-script names from grayscale crops of their own sections."""
    if not results:
        return parsed
    blocks = _extract_text_blocks(results[0])
    markers = {
        "Child": next((block for block in blocks if "родил" in block["text"].casefold()), None),
        "Father": next((block for block in blocks if block["text"].strip().casefold() == "отец"), None),
        "Mother": next((block for block in blocks if block["text"].strip().casefold() == "мать"), None),
    }
    try:
        from PIL import Image, ImageOps
        import numpy as np

        with Image.open(document_file_path) as source:
            image = source.convert("RGB")
        for role in ("Child", "Father", "Mother"):
            prefix = f"birthCertificate{role}"
            if parsed[f"{prefix}GivenName"] and parsed[f"{prefix}Patronymic"]:
                continue
            marker = markers[role]
            if marker is None:
                continue
            marker_y = (marker["box"][1] + marker["box"][3]) / 2
            names = [
                block for block in blocks
                if marker_y - (90 if role == "Child" else 5) < (block["box"][1] + block["box"][3]) / 2 < marker_y + (5 if role == "Child" else 65)
                and re.fullmatch(r"[А-Яа-яЁёA-Za-z-]+\s+[А-Яа-яЁёA-Za-z-]+", block["text"])
                and not block["text"].casefold().startswith("граждан")
                and block["box"][0] > marker["box"][2] + 60
            ]
            if len(names) != 1:
                continue
            name_block = names[0]
            left = max(0, name_block["box"][0] - 30)
            top = max(0, name_block["box"][1] - 42)
            right = min(image.width, name_block["box"][2] + 34)
            bottom = min(image.height, name_block["box"][3] + 10)
            crop = ImageOps.autocontrast(ImageOps.grayscale(image.crop((left, top, right, bottom)))).convert("RGB")
            recognized = [
                str(text).strip().translate(NAME_LOOKALIKES).title()
                for result in ocr.predict(np.asarray(crop))
                for text in result.get("rec_texts", [])
            ]
            full_names = {
                text for text in recognized
                if re.fullmatch(r"[А-ЯЁ][а-яё-]+\s+[А-ЯЁ][а-яё-]+", text)
                and not text.upper().startswith("ИМЯ ")
            }
            if len(full_names) != 1:
                continue
            surname_blocks = [
                block for block in blocks
                if 0 < name_block["box"][1] - block["box"][1] < 50
                and block["box"][3] - block["box"][1] >= (name_block["box"][3] - name_block["box"][1]) * 0.75
                and re.fullmatch(r"[А-ЯЁ][а-яё-]{3,}", block["text"])
                and block["box"][0] > marker["box"][2] + 60
            ]
            if len(surname_blocks) == 1:
                parsed[f"{prefix}Surname"] = surname_blocks[0]["text"]
            parsed[f"{prefix}GivenName"], parsed[f"{prefix}Patronymic"] = full_names.pop().split()
    except Exception:
        return parsed
    return parsed


def _retry_birth_mother_surname(
    ocr: Any, document_file_path: Path, results: list[Any], parsed: BirthCertificateData
) -> BirthCertificateData:
    """Re-reads a clipped maternal surname when the first pass lost its initial letter."""
    if not results:
        return parsed
    blocks = _extract_text_blocks(results[0])
    mother = next((block for block in blocks if block["text"].strip().casefold() == "мать"), None)
    if mother is None:
        return parsed
    marker_y = (mother["box"][1] + mother["box"][3]) / 2
    candidates = [
        block for block in blocks
        if mother["box"][1] - 35 <= (block["box"][1] + block["box"][3]) / 2 <= marker_y + 35
        and block["box"][0] > mother["box"][2] + 100
        and block["box"][3] - block["box"][1] >= (mother["box"][3] - mother["box"][1]) * 0.65
        and re.fullmatch(r"[А-Яа-яЁё-]{4,}", block["text"])
    ]
    if len(candidates) != 1:
        return parsed
    original = candidates[0]
    if not original["text"][0].islower():
        return parsed
    try:
        from PIL import Image
        import numpy as np

        with Image.open(document_file_path) as image:
            left = max(0, original["box"][0] - 64)
            top = max(0, original["box"][1] - 19)
            right = min(image.width, original["box"][2] + 80)
            bottom = min(image.height, original["box"][3] + 47)
            crop = np.asarray(image.convert("RGB").crop((left, top, right, bottom)))
        recognized = [
            str(text).strip()
            for result in ocr.predict(crop)
            for text in result.get("rec_texts", [])
        ]
    except Exception:
        return parsed

    replacements = {
        text for text in recognized
        if re.fullmatch(r"[А-ЯЁ][а-яё-]{4,}", text)
        and len(text) == len(original["text"]) + 1
        and text.casefold().endswith(original["text"].casefold())
        and text in {
            parsed["birthCertificateChildSurname"],
            parsed["birthCertificateFatherSurname"],
        }
    }
    if len(replacements) == 1:
        parsed["birthCertificateMotherSurname"] = replacements.pop()
    return parsed


def _select_document_page(
    results: Any, document_type: DocumentType
) -> PassportData | InternalPassportData | ResidencePermitData | BirthCertificateData | MarriageCertificateData:
    if document_type == "passport":
        return _select_passport_page(results)
    if document_type == "russianInternalPassport":
        return _select_internal_passport_pages(results)
    if document_type == "russianBirthCertificate":
        return merge_birth_certificate_pages([_extract_text_blocks(result) for result in results])
    if document_type == "russianMarriageCertificate":
        return merge_marriage_certificate_pages([_extract_text_blocks(result) for result in results])

    return _select_residence_permit_page(results)


def _select_internal_passport_pages(results: Any) -> InternalPassportData:
    pages = [_extract_text_blocks(result) for result in results]
    if not pages:
        raise ValueError("OCR returned no document pages.")
    return merge_internal_passport_pages(pages)


def _predict_internal_pdf_pages(ocr: Any, document_file_path: Path) -> list[Any]:
    """Renders internal-passport PDF pages at a readable resolution."""
    import numpy as np
    import pypdfium2

    results: list[Any] = []
    with pypdfium2.PdfDocument(str(document_file_path)) as pdf:
        for index in range(len(pdf)):
            page = pdf[index]
            try:
                scale = min(1.5, 3000 / max(page.get_size()))
                image = page.render(scale=scale).to_pil().convert("RGB")
                results.extend(ocr.predict(np.asarray(image)))
            finally:
                page.close()
    return results


def _read_rotated_side_numbers(
    ocr: Any, document_file_path: Path, pages: list[list[OcrTextBlock]]
) -> dict[int, list[str]]:
    """Retries only the side strip of relevant pages in both orientations."""
    from PIL import Image
    import numpy as np

    relevant_indexes = [
        index for index, blocks in enumerate(pages) if any(page_anchor_groups(blocks))
    ]
    if not relevant_indexes:
        return {}

    strips: dict[int, Image.Image] = {}
    try:
        if document_file_path.suffix.lower() == ".pdf":
            import pypdfium2

            with pypdfium2.PdfDocument(str(document_file_path)) as pdf:
                for index in relevant_indexes:
                    page = pdf[index]
                    try:
                        strips[index] = page.render(scale=1.5).to_pil().copy()
                    finally:
                        page.close()
        else:
            with Image.open(document_file_path) as source:
                strips[0] = source.copy()

        recognized: dict[int, list[str]] = {}
        for index, image in strips.items():
            left = int(image.width * 0.80)
            side = image.crop((left, 0, image.width, image.height))
            texts: list[str] = []
            for angle in (90, 270):
                rotated = side.rotate(angle, expand=True).convert("RGB")
                for result in ocr.predict(np.asarray(rotated)):
                    texts.extend(str(text) for text in result.get("rec_texts", []))
            if texts:
                recognized[index] = texts
        return recognized
    except Exception:
        return {}


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
