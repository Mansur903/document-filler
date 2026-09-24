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
_AUTHORITY_LABEL_PATTERN = re.compile(
    r"AUTHORITY|ОРГАН\s*,?\s*ВЫДАВШИЙ\s*ДОКУМЕНТ", re.IGNORECASE
)
_AUTHORITY_WORD_PATTERN = re.compile(r"[A-ZА-ЯЁІ]+", re.IGNORECASE)
_AUTHORITY_OCR_TRANSLATION = str.maketrans(
    {
        "А": "A",
        "Г": "R",
        "И": "U",
        "І": "I",
        "Н": "H",
        "О": "O",
        "Т": "T",
        "У": "Y",
    }
)


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
        "authority": _parse_authority(ocr_blocks),
        "currentNationality": _parse_country_code(line_two[10:13]),
        "dateOfBirth": _parse_date(line_two[13:19], line_two[19], reference_date, True),
        "dateOfIssue": _parse_date_of_issue(ocr_blocks),
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


def _parse_date_of_issue(ocr_blocks: list[OcrTextBlock]) -> str | None:
    for label in ocr_blocks:
        if "DATEOFISSUE" not in _compact_text(label["text"]):
            continue

        inline_value = re.split(
            r"DATE\s*OF\s*ISSUE", label["text"], maxsplit=1, flags=re.IGNORECASE
        )[-1]
        parsed_date = _parse_visual_date(inline_value)

        if parsed_date:
            return parsed_date

        for candidate in _find_values_below_label(label, ocr_blocks):
            parsed_date = _parse_visual_date(candidate)

            if parsed_date:
                return parsed_date

    return None


def _parse_authority(ocr_blocks: list[OcrTextBlock]) -> str | None:
    for label in ocr_blocks:
        if not _contains_authority_label(label["text"]):
            continue

        inline_value = _remove_authority_label(label["text"])
        parsed_inline_value = _parse_authority_value(inline_value)

        if parsed_inline_value:
            return parsed_inline_value

        candidates = [
            (vertical_gap, horizontal_offset, parsed_value)
            for vertical_gap, horizontal_offset, value in _find_ranked_values_below_label(
                label, ocr_blocks
            )
            if (parsed_value := _parse_authority_value(value)) is not None
        ]

        if not candidates:
            continue

        best_score = candidates[0][:2]
        best_values = {
            value
            for vertical_gap, horizontal_offset, value in candidates
            if (vertical_gap, horizontal_offset) == best_score
        }

        return next(iter(best_values)) if len(best_values) == 1 else None

    return None


def _parse_authority_value(value: str) -> str | None:
    cleaned = _clean_visual_value(_remove_authority_label(value))

    if not cleaned or _parse_visual_date(cleaned):
        return None

    return cleaned if sum(character.isalpha() for character in cleaned) >= 2 else None


def _contains_authority_label(value: str) -> bool:
    return bool(_AUTHORITY_LABEL_PATTERN.search(value)) or any(
        _normalize_authority_word(match.group()) == "AUTHORITY"
        for match in _AUTHORITY_WORD_PATTERN.finditer(value)
    )


def _remove_authority_label(value: str) -> str:
    without_known_labels = _AUTHORITY_LABEL_PATTERN.sub(" ", value)
    return _AUTHORITY_WORD_PATTERN.sub(
        lambda match: (
            " "
            if _normalize_authority_word(match.group()) == "AUTHORITY"
            else match.group()
        ),
        without_known_labels,
    )


def _normalize_authority_word(value: str) -> str:
    return re.sub(
        r"[^A-Z]", "", value.upper().translate(_AUTHORITY_OCR_TRANSLATION)
    )


def _parse_visual_date(value: str) -> str | None:
    normalized = value.upper().translate(_NUMERIC_OCR_CORRECTIONS)
    parts = re.search(r"(?<!\d)(\d{2})\D+(\d{2})\D+(\d{4})(?!\d)", normalized)

    if not parts:
        return None

    day, month, year = (int(part) for part in parts.groups())

    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _find_value_below_label(
    label: OcrTextBlock, ocr_blocks: list[OcrTextBlock]
) -> str | None:
    candidates = _find_values_below_label(label, ocr_blocks)
    return candidates[0] if candidates else None


def _find_values_below_label(
    label: OcrTextBlock, ocr_blocks: list[OcrTextBlock]
) -> list[str]:
    return [
        candidate[2]
        for candidate in _find_ranked_values_below_label(label, ocr_blocks)
    ]


def _find_ranked_values_below_label(
    label: OcrTextBlock, ocr_blocks: list[OcrTextBlock]
) -> list[tuple[int, int, str]]:
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

    return sorted(candidates)


def _is_visual_label(value: str) -> bool:
    if _contains_authority_label(value):
        return True

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
        "authority": None,
        "currentNationality": None,
        "dateOfBirth": None,
        "dateOfIssue": None,
        "givenName": None,
        "issuedByCountry": None,
        "numberOfTravelDocument": None,
        "placeOfBirth": None,
        "sex": None,
        "surname": None,
        "validUntil": None,
    }
