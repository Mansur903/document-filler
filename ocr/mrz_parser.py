from __future__ import annotations

from datetime import date
import re

from passport_data_model import OcrTextBlock, PassportData


_CHECK_WEIGHTS = (7, 3, 1)
_CHARACTER_VALUES = {
    **{str(value): value for value in range(10)},
    **{chr(value): value - ord("A") + 10 for value in range(ord("A"), ord("Z") + 1)},
    "<": 0,
}
_NUMERIC_OCR_CORRECTIONS = str.maketrans(
    {"B": "8", "D": "0", "I": "1", "L": "1", "O": "0", "Q": "0", "S": "5", "Z": "2"}
)
_RUSSIAN_PASSPORT_PREFIX = "P<RUS"


def parse_passport_data(
    ocr_blocks: list[OcrTextBlock], today: date | None = None
) -> PassportData:
    mrz_lines = _find_russian_mrz_lines(ocr_blocks)

    if mrz_lines is None:
        return _empty_passport_data()

    line_one, line_two = mrz_lines
    surname, given_name = _parse_names(line_one)
    reference_date = today or date.today()

    return {
        "currentNationality": _parse_country_code(line_two[10:13]),
        "dateOfBirth": _parse_date(line_two[13:19], line_two[19], reference_date, True),
        "givenName": given_name,
        "issuedByCountry": "RUS",
        "numberOfTravelDocument": _parse_document_number(line_two),
        "placeOfBirth": _parse_place_of_birth(ocr_blocks),
        "sex": line_two[20] if line_two[20] in {"F", "M"} else None,
        "surname": surname,
        "validUntil": _parse_date(line_two[21:27], line_two[27], reference_date, False),
    }


def normalize_mrz_line(value: str) -> str:
    normalized = value.upper().strip().replace(" ", "<")
    if normalized.startswith("N<RUS"):
        normalized = f"P{normalized[1:]}"

    return re.sub(r"[^A-Z0-9<]", "", normalized)


def _find_russian_mrz_lines(
    ocr_blocks: list[OcrTextBlock],
) -> tuple[str, str] | None:
    lines = [normalize_mrz_line(block["text"]) for block in ocr_blocks]

    for index, line_one in enumerate(lines):
        if not line_one.startswith(_RUSSIAN_PASSPORT_PREFIX) or "<<" not in line_one:
            continue

        for line_two in lines[index + 1 :]:
            if len(line_two) >= 44:
                return line_one[:44], line_two[:44]

    return None


def _parse_names(line_one: str) -> tuple[str | None, str | None]:
    names = line_one[5:].split("<<", maxsplit=1)

    if len(names) != 2:
        return None, None

    return _format_name(names[0]), _format_name(names[1])


def _format_name(value: str) -> str | None:
    words = [word.capitalize() for word in value.split("<") if word]
    return " ".join(words) or None


def _parse_document_number(line_two: str) -> str | None:
    number = line_two[:9].translate(_NUMERIC_OCR_CORRECTIONS)
    check_digit = line_two[9].translate(_NUMERIC_OCR_CORRECTIONS)

    if not number.isdigit() or not _has_valid_check_digit(number, check_digit):
        return None

    return number


def _parse_country_code(value: str) -> str | None:
    return value if value == "RUS" else None


def _parse_date(
    raw_value: str,
    raw_check_digit: str,
    today: date,
    is_birth_date: bool,
) -> str | None:
    value = raw_value.translate(_NUMERIC_OCR_CORRECTIONS)
    check_digit = raw_check_digit.translate(_NUMERIC_OCR_CORRECTIONS)

    if not value.isdigit() or not _has_valid_check_digit(value, check_digit):
        return None

    year = int(value[:2])
    month = int(value[2:4])
    day = int(value[4:6])
    candidates: list[date] = []

    for century in (1900, 2000):
        try:
            candidate = date(century + year, month, day)
        except ValueError:
            continue

        if not is_birth_date or candidate <= today:
            candidates.append(candidate)

    if is_birth_date:
        candidates = [candidate for candidate in candidates if _age(candidate, today) <= 120]
        selected = max(candidates) if candidates else None
    else:
        selected = min(candidates, key=lambda candidate: abs(candidate - today)) if candidates else None

    return selected.isoformat() if selected else None


def _parse_place_of_birth(ocr_blocks: list[OcrTextBlock]) -> str | None:
    for label in ocr_blocks:
        if "PLACEOFBIRTH" not in _compact_text(label["text"]):
            continue

        inline_value = re.split(
            r"PLACE\s*OF\s*BIRTH", label["text"], maxsplit=1, flags=re.IGNORECASE
        )[-1]
        inline_value = _clean_visual_value(inline_value)

        if inline_value:
            return inline_value

        candidate = _find_value_below_label(label, ocr_blocks)

        if candidate:
            return candidate

    return None


def _find_value_below_label(
    label: OcrTextBlock, ocr_blocks: list[OcrTextBlock]
) -> str | None:
    label_left, label_top, label_right, label_bottom = label["box"]
    label_height = max(label_bottom - label_top, 1)
    candidates: list[tuple[int, int, str]] = []

    for block in ocr_blocks:
        if block is label or _is_visual_label(block["text"]):
            continue

        left, top, right, _ = block["box"]
        vertical_gap = top - label_bottom
        horizontal_overlap = min(label_right, right) - max(label_left, left)

        if vertical_gap < -label_height or vertical_gap > label_height * 6:
            continue

        if horizontal_overlap <= 0 and abs(left - label_left) > label_height * 4:
            continue

        value = _clean_visual_value(block["text"])

        if not value or value in {"F", "M"} or len(normalize_mrz_line(value)) >= 40:
            continue

        candidates.append((max(vertical_gap, 0), abs(left - label_left), value))

    return min(candidates)[2] if candidates else None


def _is_visual_label(value: str) -> bool:
    compact = _compact_text(value)
    return any(
        marker in compact
        for marker in (
            "DATEOFBIRTH",
            "DATEOFEXPIRY",
            "DATEOFISSUE",
            "GIVENNAME",
            "NATIONALITY",
            "PASSPORTNO",
            "PLACEOFBIRTH",
            "SURNAME",
        )
    )


def _compact_text(value: str) -> str:
    return re.sub(r"[^A-Z]", "", value.upper())


def _clean_visual_value(value: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", value).strip(" /:-")
    return cleaned or None


def _has_valid_check_digit(value: str, check_digit: str) -> bool:
    return check_digit.isdigit() and _calculate_check_digit(value) == int(check_digit)


def _calculate_check_digit(value: str) -> int:
    return sum(
        _CHARACTER_VALUES[character] * _CHECK_WEIGHTS[index % len(_CHECK_WEIGHTS)]
        for index, character in enumerate(value)
    ) % 10


def _age(birth_date: date, today: date) -> int:
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


def _empty_passport_data() -> PassportData:
    return {
        "currentNationality": None,
        "dateOfBirth": None,
        "givenName": None,
        "issuedByCountry": None,
        "numberOfTravelDocument": None,
        "placeOfBirth": None,
        "sex": None,
        "surname": None,
        "validUntil": None,
    }
