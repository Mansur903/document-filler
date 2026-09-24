from __future__ import annotations

from datetime import date
import re
from typing import Callable

from passport_data_model import OcrTextBlock, ResidencePermitData


_LABELS = {
    "residencepermitID": "UIDNO",
    "visaID": "FILENO",
    "visaValidUntil": "EXPIRYDATE",
    "currentOccupation": "PROFESSION",
    "employer": "EMPLOYER",
}
_NUMERIC_OCR_CORRECTIONS = str.maketrans(
    {"B": "8", "D": "0", "I": "1", "L": "1", "O": "0", "Q": "0", "S": "5", "Z": "2"}
)


def has_residence_permit_anchors(ocr_blocks: list[OcrTextBlock]) -> bool:
    """Return whether a page contains enough permit labels to identify the layout."""
    matched_labels = {
        marker
        for block in ocr_blocks
        for marker in _LABELS.values()
        if marker in _compact_text(block["text"])
    }
    return len(matched_labels) >= 2


def parse_residence_permit_data(
    ocr_blocks: list[OcrTextBlock],
) -> ResidencePermitData:
    """Extract the supported UAE Residence Permit fields from positioned OCR text."""
    return {
        "currentOccupation": _parse_field(
            "currentOccupation", ocr_blocks, _parse_text_value
        ),
        "employer": _parse_field("employer", ocr_blocks, _parse_text_value),
        "residencepermitID": _parse_field(
            "residencepermitID", ocr_blocks, _parse_uid
        ),
        "visaID": _parse_field("visaID", ocr_blocks, _parse_file_number),
        "visaValidUntil": _parse_field(
            "visaValidUntil", ocr_blocks, _parse_visual_date
        ),
    }


def _parse_field(
    field: str,
    ocr_blocks: list[OcrTextBlock],
    parser: Callable[[str], str | None],
) -> str | None:
    marker = _LABELS[field]

    for label in ocr_blocks:
        if marker not in _compact_text(label["text"]):
            continue

        inline_value = _remove_label_text(label["text"], marker)
        parsed_inline_value = parser(inline_value)

        candidates = _rank_nearby_values(label, ocr_blocks, parser)
        label_starts_with_marker = _compact_text(label["text"]).startswith(marker)

        if parsed_inline_value and (label_starts_with_marker or not candidates):
            return parsed_inline_value

        if not candidates:
            continue

        best_score, best_value = candidates[0]

        if (
            len(candidates) > 1
            and candidates[1][0][0] == best_score[0]
            and (
                candidates[1][0][1]
                + candidates[1][0][2]
                - best_score[1]
                - best_score[2]
                <= _box_height(label["box"])
            )
            and candidates[1][1] != best_value
        ):
            return None

        return best_value

    if field in {"residencepermitID", "visaID", "visaValidUntil"}:
        return _find_unique_value(ocr_blocks, parser)

    return None


def _find_unique_value(
    ocr_blocks: list[OcrTextBlock], parser: Callable[[str], str | None]
) -> str | None:
    values = {
        parsed_value
        for block in ocr_blocks
        if not _is_label(block["text"])
        if (parsed_value := parser(block["text"])) is not None
    }
    return next(iter(values)) if len(values) == 1 else None


def _rank_nearby_values(
    label: OcrTextBlock,
    ocr_blocks: list[OcrTextBlock],
    parser: Callable[[str], str | None],
) -> list[tuple[tuple[int, int, int], str]]:
    label_left, label_top, label_right, label_bottom = label["box"]
    label_height = _box_height(label["box"])
    label_center_x = (label_left + label_right) // 2
    label_center_y = (label_top + label_bottom) // 2
    candidates: list[tuple[tuple[int, int, int], str]] = []

    for block in ocr_blocks:
        if block is label or _is_label(block["text"]):
            continue

        parsed_value = parser(block["text"])

        if not parsed_value:
            continue

        left, top, right, bottom = block["box"]
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        vertical_overlap = min(label_bottom, bottom) - max(label_top, top)
        same_row = vertical_overlap > 0 or abs(center_y - label_center_y) <= label_height * 2
        horizontal_gap = max(label_left - right, left - label_right, 0)
        vertical_gap = max(label_top - bottom, top - label_bottom, 0)
        horizontal_overlap = min(label_right, right) - max(label_left, left)

        if same_row and right <= label_left + label_height:
            score = (0, horizontal_gap, abs(center_y - label_center_y))
        elif same_row and left >= label_right - label_height:
            score = (1, horizontal_gap, abs(center_y - label_center_y))
        elif (
            horizontal_overlap > 0
            or abs(center_x - label_center_x) <= label_height * 12
        ) and vertical_gap <= label_height * 8:
            score = (2, vertical_gap, abs(center_x - label_center_x))
        else:
            continue

        candidates.append((score, parsed_value))

    return sorted(candidates, key=lambda candidate: candidate[0])


def _remove_label_text(value: str, marker: str) -> str:
    words = {
        "UIDNO": r"U\s*I\s*D\s*(?:NO|NUMBER)?\.?",
        "FILENO": r"FILE\s*(?:NO|NUMBER)?\.?",
        "EXPIRYDATE": r"EXPIRY\s*DATE",
        "PROFESSION": r"PROFESSION",
        "EMPLOYER": r"EMPLOYER",
    }
    return re.sub(words[marker], " ", value, flags=re.IGNORECASE)


def _parse_uid(value: str) -> str | None:
    if re.search(r"[/.-]", value):
        return None

    normalized = re.sub(r"\s+", "", value.upper()).translate(
        _NUMERIC_OCR_CORRECTIONS
    )
    digits = re.sub(r"\D", "", normalized)
    return digits if 12 <= len(digits) <= 20 else None


def _parse_file_number(value: str) -> str | None:
    normalized = value.upper().translate(_NUMERIC_OCR_CORRECTIONS)
    normalized = re.sub(r"\s*([/.-])\s*", r"\1", normalized)
    match = re.search(
        r"(?<!\d)(\d{2,4}([/.-])\d{4}\2\d{5,10})(?!\d)", normalized
    )
    return match.group(1) if match else None


def _parse_visual_date(value: str) -> str | None:
    normalized = value.upper().translate(_NUMERIC_OCR_CORRECTIONS)
    match = re.search(
        r"(?<!\d)(\d{2,4})\D+(\d{2})\D+(\d{2,4})(?!\d)", normalized
    )

    if not match:
        return None

    first, second, third = match.groups()

    if len(first) == 4 and len(third) == 2:
        year, month, day = int(first), int(second), int(third)
    elif len(first) == 2 and len(third) == 4:
        day, month, year = int(first), int(second), int(third)
    else:
        return None

    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _parse_text_value(value: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", value).strip(" /:-")
    latin_letters = re.findall(r"[A-Z]", cleaned.upper())

    if not cleaned or len(latin_letters) < 2:
        return None

    return cleaned


def _is_label(value: str) -> bool:
    compact = _compact_text(value)
    return any(marker in compact for marker in _LABELS.values())


def _compact_text(value: str) -> str:
    return re.sub(r"[^A-Z]", "", value.upper())


def _box_height(box: tuple[int, int, int, int]) -> int:
    return max(box[3] - box[1], 1)
