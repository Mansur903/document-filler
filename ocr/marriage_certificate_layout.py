"""Reads the positional layout used by Russian marriage-certificate blanks."""

from __future__ import annotations

from datetime import date
import re
from typing import cast

from passport_data_model import MarriageCertificateData, OcrTextBlock


MONTHS = {
    month: index for index, month in enumerate(
        ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"),
        start=1,
    )
}
NATIONALITY_LOOKALIKES = str.maketrans({
    "p": "р", "u": "у", "y": "у", "c": "с", "s": "с", "k": "к", "a": "а", "e": "е", "o": "о",
})
SERIES_LOOKALIKES = str.maketrans({"Φ": "Ф", "P": "Р", "F": "Ф", "B": "В", "A": "А", "H": "Н", "K": "К"})
PERSON_NAME = re.compile(r"[А-ЯЁ][а-яё-]+\s+[А-ЯЁ][а-яё-]+", re.IGNORECASE)
SURNAME = re.compile(r"[А-ЯЁ][а-яё-]{2,}", re.IGNORECASE)
DATE_TEXT = re.compile(r"(?<!\d)(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})(?!\d)", re.IGNORECASE)
SERIES_NUMBER = re.compile(r"\b([IVX]{1,4})[-–]([А-ЯA-ZΦ]{2,4})\s*(?:№|N|NO)\s*(\d{4,10})\b", re.IGNORECASE)


def parse_marriage_certificate_layout(blocks: list[OcrTextBlock]) -> MarriageCertificateData | None:
    """Parses spouses and registration from values printed around small labels."""
    surname_labels = [block for block in sorted(blocks, key=_mid_y) if re.fullmatch(r"\(?фамилия\)?", block["text"].strip(), re.IGNORECASE)]
    marriage_marker = _find(blocks, r"ЗАКЛЮЧИЛИ\s+БРАК")
    after_marker = _find(blocks, r"ПОСЛЕ\s+ЗАКЛЮЧЕНИЯ\s+БРАКА")
    if len(surname_labels) != 2 or marriage_marker is None or after_marker is None:
        return None
    if _mid_y(surname_labels[1]) >= _mid_y(marriage_marker):
        return None

    result: dict[str, str | None] = {key: None for key in MarriageCertificateData.__annotations__}
    for role, label in enumerate(surname_labels, start=1):
        prefix = f"marriageCertificateSpouse{role}"
        result[f"{prefix}SurnameBefore"] = _surname_before(blocks, label)
        name = _name_after(blocks, label)
        if name:
            result[f"{prefix}GivenNameBefore"], result[f"{prefix}PatronymicBefore"] = name
        citizenship_label = _next_label(blocks, label, r"ГРАЖДАНСТВО")
        if citizenship_label:
            result[f"{prefix}Citizenship"] = _value_above(blocks, citizenship_label, 80)
        date_label = _next_label(blocks, label, r"ДАТА\s+РОЖДЕНИЯ")
        if date_label:
            result[f"{prefix}DateOfBirth"] = _split_date(_near(blocks, _mid_y(date_label) - 30, 55))
        nationality_label = _next_label(blocks, label, r"НАЦИОНАЛЬНОСТЬ")
        if nationality_label:
            result[f"{prefix}Nationality"] = _nationality(blocks, nationality_label)
        place_label = _next_label(blocks, label, r"МЕСТО\s+РОЖДЕНИЯ")
        if place_label:
            result[f"{prefix}PlaceOfBirth"] = _place_above(blocks, place_label)

    result["marriageCertificateMarriageDate"] = _inline_date(blocks, marriage_marker)
    record_marker = _find(blocks, r"СОСТАВЛЕНА\s+ЗАПИСЬ\s+АКТА\s+О\s+ЗАКЛЮЧЕНИИ\s+БРАКА")
    record_date_marker = _find(blocks, r"^О\s+ЧЕМ$")
    if record_date_marker:
        result["marriageCertificateRecordDate"] = _split_date(_near(blocks, _mid_y(record_date_marker), 45))
    if record_marker:
        result["marriageCertificateRecordNumber"] = _record_number(blocks, record_marker)

    husband = _find(blocks, r"^МУЖУ$")
    wife = _find(blocks, r"^ЖЕН[ЕЁE]$")
    if husband:
        result["marriageCertificateSpouse1SurnameAfter"] = _surname_near_marker(blocks, husband)
    if wife:
        result["marriageCertificateSpouse2SurnameAfter"] = _surname_near_marker(blocks, wife)

    registration_marker = _find(blocks, r"МЕСТО\s+ГОСУДАРСТВЕННОЙ\s+РЕГИСТРАЦИИ")
    issue_place_marker = _find(blocks, r"МЕСТО\s+ВЫДАЧИ\s+СВИДЕТЕЛЬСТВА")
    if registration_marker and issue_place_marker:
        office_lines = [
            re.sub(r"^\d{6,10}\s+", "", block["text"].strip())
            for block in sorted(blocks, key=_mid_y)
            if _mid_y(registration_marker) - 20 <= _mid_y(block) < _mid_y(issue_place_marker) - 55
            and block["box"][0] >= registration_marker["box"][2] - 50
            and block["box"][3] - block["box"][1] >= 35
            and not block["text"].startswith("(")
            and "ГОСУДАРСТВЕННАЯ РЕГИСТРАЦИЯ" not in block["text"].upper()
        ]
        result["marriageCertificateRegistryOffice"] = " ".join(office_lines) or None

    issue_date_marker = _find(blocks, r"ДАТА\s+ВЫДАЧИ")
    if issue_date_marker:
        result["marriageCertificateIssueDate"] = _split_date(_near(blocks, _mid_y(issue_date_marker), 55))
    for block in sorted(blocks, key=_mid_y, reverse=True):
        match = SERIES_NUMBER.search(block["text"])
        if match:
            result["marriageCertificateSeries"] = f"{match.group(1).upper()}-{match.group(2).upper().translate(SERIES_LOOKALIKES)}"
            result["marriageCertificateNumber"] = match.group(3)
            break
    return cast(MarriageCertificateData, result)


def _mid_y(block: OcrTextBlock) -> float:
    return (block["box"][1] + block["box"][3]) / 2


def _near(blocks: list[OcrTextBlock], y: float, distance: float) -> list[OcrTextBlock]:
    return [block for block in blocks if abs(_mid_y(block) - y) <= distance]


def _find(blocks: list[OcrTextBlock], pattern: str) -> OcrTextBlock | None:
    matcher = re.compile(pattern, re.IGNORECASE)
    return next((block for block in blocks if matcher.search(block["text"].strip())), None)


def _next_label(blocks: list[OcrTextBlock], after: OcrTextBlock, pattern: str) -> OcrTextBlock | None:
    matcher = re.compile(pattern, re.IGNORECASE)
    return next((block for block in sorted(blocks, key=_mid_y) if _mid_y(after) < _mid_y(block) < _mid_y(after) + 300 and matcher.search(block["text"])), None)


def _surname_before(blocks: list[OcrTextBlock], label: OcrTextBlock) -> str | None:
    candidates = [
        block["text"].strip().title()
        for block in blocks
        if 0 < _mid_y(label) - _mid_y(block) < 100
        and abs((block["box"][0] + block["box"][2]) / 2 - (label["box"][0] + label["box"][2]) / 2) < 220
        and SURNAME.fullmatch(block["text"].strip())
        and block["box"][3] - block["box"][1] > (label["box"][3] - label["box"][1]) * 1.2
    ]
    return candidates[0] if len(candidates) == 1 else None


def _name_after(blocks: list[OcrTextBlock], label: OcrTextBlock) -> tuple[str, str] | None:
    candidates = [
        block["text"].strip().title()
        for block in blocks
        if 0 < _mid_y(block) - _mid_y(label) < 85
        and PERSON_NAME.fullmatch(block["text"].strip())
        and block["box"][3] - block["box"][1] > (label["box"][3] - label["box"][1]) * 1.3
        and "ФЕДЕРАЦИЯ" not in block["text"].upper()
    ]
    return tuple(candidates[0].split()) if len(candidates) == 1 else None


def _value_above(blocks: list[OcrTextBlock], label: OcrTextBlock, distance: float) -> str | None:
    candidates = [
        block["text"].strip()
        for block in blocks
        if 0 < _mid_y(label) - _mid_y(block) < distance
        and block["box"][3] - block["box"][1] > (label["box"][3] - label["box"][1]) * 1.3
        and re.search(r"РОССИЙСК|РОССИИ", block["text"].upper())
    ]
    return "Российская Федерация" if len(candidates) == 1 else None


def _nationality(blocks: list[OcrTextBlock], label: OcrTextBlock) -> str | None:
    candidates = {
        block["text"].strip().lower().translate(NATIONALITY_LOOKALIKES)
        for block in blocks
        if 0 < _mid_y(label) - _mid_y(block) < 75
        and abs((block["box"][0] + block["box"][2]) / 2 - (label["box"][0] + label["box"][2]) / 2) < 220
        and re.fullmatch(r"[А-Яа-яЁёA-Za-z]{4,}", block["text"].strip())
    }
    return next(iter(candidates)) if len(candidates) == 1 else None


def _place_above(blocks: list[OcrTextBlock], label: OcrTextBlock) -> str | None:
    candidates = [
        block["text"].strip()
        for block in blocks
        if 0 < _mid_y(label) - _mid_y(block) < 90
        and block["box"][3] - block["box"][1] > (label["box"][3] - label["box"][1]) * 1.3
        and "," in block["text"]
        and len(block["text"]) > 18
    ]
    return candidates[0] if len(candidates) == 1 else None


def _inline_date(blocks: list[OcrTextBlock], marker: OcrTextBlock) -> str | None:
    candidates = [block["text"] for block in _near(blocks, _mid_y(marker), 55) if DATE_TEXT.search(block["text"])]
    return _date_text(candidates[0]) if len(candidates) == 1 else None


def _date_text(value: str) -> str | None:
    match = DATE_TEXT.search(value)
    if not match:
        return None
    try:
        return date(int(match.group(3)), MONTHS[match.group(2).lower()], int(match.group(1))).isoformat()
    except ValueError:
        return None


def _split_date(blocks: list[OcrTextBlock]) -> str | None:
    years = {int(block["text"]) for block in blocks if re.fullmatch(r"(?:19|20)\d{2}", block["text"].strip())}
    days = {int(block["text"]) for block in blocks if re.fullmatch(r"\d{1,2}", block["text"].strip())}
    months = {index for block in blocks for month, index in MONTHS.items() if block["text"].strip().lower() == month}
    if len(years) != 1 or len(days) != 1 or len(months) != 1:
        return None
    try:
        return date(next(iter(years)), next(iter(months)), next(iter(days))).isoformat()
    except ValueError:
        return None


def _record_number(blocks: list[OcrTextBlock], marker: OcrTextBlock) -> str | None:
    candidates = {
        block["text"].strip()
        for block in _near(blocks, _mid_y(marker), 60)
        if block["box"][0] > marker["box"][2]
        and re.fullmatch(r"\d{1,25}", block["text"].strip())
    }
    return next(iter(candidates)) if len(candidates) == 1 else None


def _surname_near_marker(blocks: list[OcrTextBlock], marker: OcrTextBlock) -> str | None:
    candidates = {
        block["text"].strip().title()
        for block in _near(blocks, _mid_y(marker), 50)
        if block["box"][0] > marker["box"][2] + 200
        and SURNAME.fullmatch(block["text"].strip())
        and block["box"][3] - block["box"][1] >= marker["box"][3] - marker["box"][1]
    }
    return next(iter(candidates)) if len(candidates) == 1 else None
