"""Extracts Russian internal passport fields from positioned OCR text blocks."""

from __future__ import annotations

from datetime import date
from difflib import SequenceMatcher
import re
from mrz_parser import normalize_mrz_line
from passport_data_model import InternalPassportData, OcrTextBlock


LABEL_PATTERNS = {
    "authority": re.compile(r"ПАСПОРТ\s*ВЫДАН", re.IGNORECASE),
    "dateOfBirth": re.compile(r"ДАТА\s*РОЖДЕНИЯ", re.IGNORECASE),
    "dateOfIssue": re.compile(r"ДАТА\s*ВЫДАЧИ", re.IGNORECASE),
    "givenName": re.compile(r"^ИМЯ\b", re.IGNORECASE),
    "patronymic": re.compile(r"ОТЧЕСТВО", re.IGNORECASE),
    "placeOfBirth": re.compile(r"МЕСТО\s*РОЖДЕНИЯ", re.IGNORECASE),
    "sex": re.compile(r"^ПОЛ\b", re.IGNORECASE),
    "subdivisionCode": re.compile(r"КОД\s*ПОДРАЗДЕЛЕНИЯ", re.IGNORECASE),
    "surname": re.compile(r"ФАМИЛИЯ", re.IGNORECASE),
}
LABEL_TEXT = {
    "authority": "ПАСПОРТВЫДАН",
    "dateOfBirth": "ДАТАРОЖДЕНИЯ",
    "dateOfIssue": "ДАТАВЫДАЧИ",
    "givenName": "ИМЯ",
    "patronymic": "ОТЧЕСТВО",
    "placeOfBirth": "МЕСТОРОЖДЕНИЯ",
    "sex": "ПОЛ",
    "subdivisionCode": "КОДПОДРАЗДЕЛЕНИЯ",
    "surname": "ФАМИЛИЯ",
}
LATIN_LOOKALIKES = str.maketrans(
    {"A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "I": "И", "K": "К", "L": "Л", "M": "М", "N": "Н", "O": "О", "P": "Р", "T": "Т", "X": "Х", "Y": "У"}
)
NAME_OCR_TRANSLATION = str.maketrans(
    {"A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "I": "И", "J": "Л", "K": "К", "L": "Л", "M": "М", "N": "И", "O": "О", "P": "Р", "T": "Т", "X": "Х", "Y": "У", "3": "З"}
)
DATE_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\s*[.\-/]\s*(\d{1,2})\s*[.\-/]\s*(\d{4})(?!\d)")
CODE_PATTERN = re.compile(r"(?<!\d)(\d{3})\s*[-–— ]\s*(\d{3})(?!\d)")
CYRILLIC_PATTERN = re.compile(r"[А-ЯЁ][А-ЯЁ\-]*", re.IGNORECASE)
SIDE_NUMBER_PATTERN = re.compile(r"(?<!\d)(\d{4})\s*(\d{6})(?!\d)")
SEX_PATTERN = re.compile(r"\b(ЖЕН\.?|ЖЕНСКИЙ|МУЖ\.?|МУЖСКОЙ)\b", re.IGNORECASE)


def empty_internal_passport_data() -> InternalPassportData:
    return {
        "authority": None,
        "dateOfBirth": None,
        "dateOfIssue": None,
        "givenName": None,
        "internalPassportNumber": None,
        "internalPassportSeries": None,
        "patronymic": None,
        "placeOfBirth": None,
        "sex": None,
        "subdivisionCode": None,
        "surname": None,
    }


def page_anchor_groups(blocks: list[OcrTextBlock]) -> tuple[bool, bool]:
    if any(normalize_mrz_line(block["text"]).startswith("P<RUS") for block in blocks):
        return False, False
    labels = _find_labels(blocks)
    upper = sum(
        key in labels for key in ("authority", "dateOfIssue", "subdivisionCode")
    ) >= 2
    lower = sum(
        key in labels
        for key in ("surname", "givenName", "patronymic", "dateOfBirth", "placeOfBirth")
    ) >= 2
    return upper, lower


def parse_internal_passport_data(
    blocks: list[OcrTextBlock],
    side_number_candidates: list[str] | None = None,
) -> InternalPassportData:
    result = empty_internal_passport_data()
    upper, lower = page_anchor_groups(blocks)

    if not upper and not lower:
        return result

    labels = _find_labels(blocks)
    result["surname"] = _parse_name("surname", labels, blocks) if lower else None
    result["givenName"] = _parse_name("givenName", labels, blocks) if lower else None
    result["patronymic"] = _parse_name("patronymic", labels, blocks) if lower else None
    result["sex"] = _parse_sex(labels, blocks) if lower else None
    result["dateOfBirth"] = _parse_date_field("dateOfBirth", labels, blocks) if lower else None
    result["placeOfBirth"] = _parse_multiline("placeOfBirth", labels, blocks, 3) if lower else None
    result["dateOfIssue"] = _parse_date_field("dateOfIssue", labels, blocks) if upper else None
    result["subdivisionCode"] = _parse_code(labels, blocks) if upper else None
    result["authority"] = _parse_authority(labels, blocks) if upper else None

    side_numbers = _side_numbers(blocks)
    if side_number_candidates:
        side_numbers.update(_numbers_from_strings(side_number_candidates))
    if len(side_numbers) == 1:
        series, number = next(iter(side_numbers))
        result["internalPassportSeries"] = series
        result["internalPassportNumber"] = number

    return result


def merge_internal_passport_pages(
    pages: list[list[OcrTextBlock]],
    side_number_candidates: dict[int, list[str]] | None = None,
) -> InternalPassportData:
    """Selects one compatible upper/lower pair without mixing unrelated pages."""
    candidates: list[tuple[bool, bool, InternalPassportData]] = []

    for index, blocks in enumerate(pages):
        upper, lower = page_anchor_groups(blocks)
        if upper or lower:
            parsed = parse_internal_passport_data(
                blocks, (side_number_candidates or {}).get(index)
            )
            candidates.append((upper, lower, parsed))

    if not candidates:
        return empty_internal_passport_data()

    complete = [item for item in candidates if item[0] and item[1]]
    if len(complete) == 1:
        return complete[0][2]
    if len(complete) > 1:
        return empty_internal_passport_data()

    upper_pages = [item[2] for item in candidates if item[0]]
    lower_pages = [item[2] for item in candidates if item[1]]
    if len(upper_pages) > 1 or len(lower_pages) > 1:
        return empty_internal_passport_data()
    if not upper_pages:
        return lower_pages[0]
    if not lower_pages:
        return upper_pages[0]

    upper = upper_pages[0]
    lower = lower_pages[0]
    for key in ("internalPassportSeries", "internalPassportNumber"):
        if upper[key] and lower[key] and upper[key] != lower[key]:
            return lower

    merged = empty_internal_passport_data()
    for key in merged:
        merged[key] = lower[key] or upper[key]
    return merged


def _find_labels(blocks: list[OcrTextBlock]) -> dict[str, OcrTextBlock]:
    found: dict[str, tuple[float, OcrTextBlock]] = {}
    candidates = list(blocks)
    for first in blocks:
        for second in blocks:
            if first is second:
                continue
            left = first["box"]
            right = second["box"]
            height = max(12, left[3] - left[1])
            if (
                abs(left[0] - right[0]) <= height * 1.5
                and left[1] < right[1] <= left[3] + height * 1.2
            ):
                candidates.append(
                    {
                        "box": (
                            min(left[0], right[0]),
                            left[1],
                            max(left[2], right[2]),
                            right[3],
                        ),
                        "text": first["text"] + " " + second["text"],
                    }
                )

    for block in candidates:
        compact = _compact_label(block["text"])
        for key, expected in LABEL_TEXT.items():
            score = _label_score(key, compact, expected)
            if score >= 0.75 and (key not in found or score > found[key][0]):
                found[key] = (score, block)
    return {key: value for key, (_, value) in found.items()}


def _normalize(value: str) -> str:
    return " ".join(value.upper().translate(LATIN_LOOKALIKES).replace("Ё", "Е").split())


def _compact_label(value: str) -> str:
    return "".join(character for character in _normalize(value) if "А" <= character <= "Я")


def _label_score(key: str, value: str, expected: str) -> float:
    if key == "givenName" and value in {"ИМЯ", "НМА"}:
        return 1.0
    if key == "sex" and value in {"ПОЛ", "ИЛОХ", "НЛОХ"}:
        return 1.0
    if len(value) < len(expected) * 0.7 or len(value) > len(expected) * 1.5:
        return 0.0
    return SequenceMatcher(None, value, expected).ratio()


def _is_label_component(block: OcrTextBlock, labels: dict[str, OcrTextBlock]) -> bool:
    x1, y1, x2, y2 = block["box"]
    return any(
        x1 >= label["box"][0]
        and y1 >= label["box"][1]
        and x2 <= label["box"][2]
        and y2 <= label["box"][3]
        for label in labels.values()
    )


def _related_values(
    key: str, labels: dict[str, OcrTextBlock], blocks: list[OcrTextBlock], max_lines: int = 1
) -> list[str]:
    label = labels.get(key)
    if label is None:
        return []

    label_box = label["box"]
    height = max(12, label_box[3] - label_box[1])
    next_label_y = min(
        (
            block["box"][1]
            for other_key, block in labels.items()
            if other_key != key and block["box"][1] > label_box[3] + height / 3
        ),
        default=label_box[3] + height * (max_lines + 1.8),
    )
    bottom = min(next_label_y, label_box[3] + height * (max_lines + 1.8))
    values: list[OcrTextBlock] = []
    inline = LABEL_PATTERNS[key].sub("", _normalize(label["text"]), count=1).strip(" .:-")

    for block in blocks:
        if _is_label_component(block, labels):
            continue
        x1, y1, _, y2 = block["box"]
        same_row = y1 <= label_box[3] + height / 2 and y2 >= label_box[1] - height / 2
        below = label_box[3] < y1 < bottom
        if (same_row or below) and x1 >= label_box[0] - height:
            values.append(block)

    values.sort(key=lambda block: (block["box"][1], block["box"][0]))
    return ([inline] if inline else []) + [block["text"].strip() for block in values]


def _parse_name(
    key: str, labels: dict[str, OcrTextBlock], blocks: list[OcrTextBlock]
) -> str | None:
    label = labels.get(key)
    if label is None:
        return None
    x1, y1, x2, y2 = label["box"]
    height = max(12, y2 - y1)
    candidates = sorted(
        (
            block for block in blocks
            if not _is_label_component(block, labels)
            and block["box"][0] >= x2 - height
            and y1 - height <= block["box"][1] <= y2 + height * 1.2
        ),
        key=lambda block: (abs(block["box"][1] - y1), block["box"][0]),
    )
    for block in candidates:
        value = block["text"].upper().translate(NAME_OCR_TRANSLATION)
        words = CYRILLIC_PATTERN.findall(value)
        if words and not any(pattern.search(_normalize(value)) for pattern in LABEL_PATTERNS.values()):
            return " ".join(words)
    return None


def _parse_multiline(
    key: str,
    labels: dict[str, OcrTextBlock],
    blocks: list[OcrTextBlock],
    max_lines: int,
) -> str | None:
    values = []
    for value in _related_values(key, labels, blocks, max_lines):
        if CYRILLIC_PATTERN.search(value) and not any(
            pattern.search(_normalize(value)) for pattern in LABEL_PATTERNS.values()
        ):
            values.append(" ".join(value.split()).upper())
    return " ".join(values) or None


def _parse_authority(
    labels: dict[str, OcrTextBlock], blocks: list[OcrTextBlock]
) -> str | None:
    label = labels.get("authority")
    if label is None:
        return None
    issue_y = labels.get("dateOfIssue", label)["box"][1]
    top = max(0, label["box"][1] - 3 * (label["box"][3] - label["box"][1]))
    values = [
        block["text"].strip()
        for block in sorted(blocks, key=lambda item: (item["box"][1], item["box"][0]))
        if not _is_label_component(block, labels)
        and top <= block["box"][1] < issue_y
        and block["box"][0] >= label["box"][0]
        and CYRILLIC_PATTERN.search(block["text"])
        and "РОССИЙСКАЯ ФЕДЕРАЦИЯ" not in _normalize(block["text"])
    ]
    return " ".join(" ".join(value.split()) for value in values).upper() or None


def _parse_sex(labels: dict[str, OcrTextBlock], blocks: list[OcrTextBlock]) -> str | None:
    for value in _related_values("sex", labels, blocks):
        match = SEX_PATTERN.search(_normalize(value))
        if match:
            return "F" if match.group().startswith("Ж") else "M"
    return None


def _parse_date_field(
    key: str, labels: dict[str, OcrTextBlock], blocks: list[OcrTextBlock]
) -> str | None:
    values = {
        parsed
        for value in _related_values(key, labels, blocks)
        if (parsed := _parse_date(value)) is not None
    }
    return next(iter(values)) if len(values) == 1 else None


def _parse_date(value: str) -> str | None:
    match = DATE_PATTERN.search(value)
    if not match:
        return None
    day, month, year = map(int, match.groups())
    try:
        parsed = date(year, month, day)
    except ValueError:
        return None
    return parsed.isoformat()


def _parse_code(labels: dict[str, OcrTextBlock], blocks: list[OcrTextBlock]) -> str | None:
    values = {
        f"{match.group(1)}-{match.group(2)}"
        for value in _related_values("subdivisionCode", labels, blocks)
        if (match := CODE_PATTERN.search(value)) is not None
    }
    return next(iter(values)) if len(values) == 1 else None


def _side_numbers(blocks: list[OcrTextBlock]) -> set[tuple[str, str]]:
    if not blocks:
        return set()
    max_x = max(block["box"][2] for block in blocks)
    side = [
        block for block in blocks
        if block["box"][0] >= max_x * 0.82
        and re.fullmatch(r"[\d\s]+", block["text"])
    ]
    side.sort(key=lambda block: block["box"][1])
    candidates = _numbers_from_strings([block["text"] for block in side])
    for start in range(len(side) - 2):
        pieces = [re.sub(r"\D", "", block["text"]) for block in side[start : start + 3]]
        if [len(piece) for piece in pieces] == [2, 2, 6]:
            candidates.add((pieces[0] + pieces[1], pieces[2]))
    return candidates


def _numbers_from_strings(values: list[str]) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for value in values:
        match = SIDE_NUMBER_PATTERN.search(value)
        if match:
            result.add((match.group(1), match.group(2)))
    for start in range(len(values) - 2):
        pieces = [re.sub(r"\s", "", value) for value in values[start : start + 3]]
        if [len(piece) for piece in pieces] == [2, 2, 6] and all(
            piece.isdigit() for piece in pieces
        ):
            result.add((pieces[0] + pieces[1], pieces[2]))
    return result
