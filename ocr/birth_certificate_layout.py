"""Reads the positional layout used by Russian birth-certificate blanks."""

from __future__ import annotations

from datetime import date
import re
from typing import cast

from passport_data_model import BirthCertificateData, OcrTextBlock


MONTHS = {
    month: index for index, month in enumerate(
        ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"),
        start=1,
    )
}
VISUAL_DATE = re.compile(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4})(?!\d)")
PERSON_NAME = re.compile(r"[А-ЯЁ][а-яё-]+(?:\s+[А-ЯЁ][а-яё-]+){1,2}", re.IGNORECASE)
SURNAME = re.compile(r"[А-ЯЁ][а-яё-]+", re.IGNORECASE)
SERIES_NUMBER = re.compile(r"\b([IVX]{1,4}-[А-ЯA-Z]{2,4})\s*(?:№|N|NO|NО)\s*(\d{4,10})\b", re.IGNORECASE)
LOOKALIKES = str.maketrans({"A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "K": "К", "M": "М", "O": "О", "P": "Р", "T": "Т", "X": "Х", "Y": "У"})


def parse_birth_certificate_layout(blocks: list[OcrTextBlock]) -> BirthCertificateData | None:
    """Parses values placed above their small printed labels on a certificate blank."""
    if not _find(blocks, r"РОДИЛ") or not _find(blocks, r"МЕСТО\s+ГОСУДАРСТВЕННОЙ\s+РЕГИСТРАЦИИ"):
        return None

    title = _find(blocks, r"О\s+РОЖДЕНИИ")
    birth_marker = _find(blocks, r"РОДИЛ")
    place_marker = _find(blocks, r"МЕСТО\s+РОЖДЕНИЯ")
    record_marker = _find(blocks, r"СОСТАВЛЕНА\s+ЗАПИСЬ\s+АКТА")
    father_marker = _find(blocks, r"^ОТЕЦ$")
    mother_marker = _find(blocks, r"^МАТЬ$")
    registration_marker = _find(blocks, r"МЕСТО\s+ГОСУДАРСТВЕННОЙ\s+РЕГИСТРАЦИИ")
    issue_marker = _find(blocks, r"ВЫДАЧИ")
    if not all((title, birth_marker, place_marker, record_marker, father_marker, mother_marker, registration_marker, issue_marker)):
        return None

    minimum_height = max(8, (title["box"][3] - title["box"][1]) * 0.45)
    birth_date = _visual_date(_near(blocks, _mid_y(birth_marker), 45))
    birth_date_block = next((block for block in _near(blocks, _mid_y(birth_marker), 45) if VISUAL_DATE.search(block["text"])), None)
    child_end = _mid_y(birth_date_block) - 8 if birth_date_block else _mid_y(birth_marker)
    child_name = _person_name(blocks, _mid_y(title), child_end, minimum_height)

    father_citizenship = _citizenship_block(blocks, _mid_y(father_marker), _mid_y(mother_marker))
    mother_citizenship = _citizenship_block(blocks, _mid_y(mother_marker), _mid_y(registration_marker))
    father_name = _person_name(blocks, _mid_y(father_marker) - 30, _mid_y(father_citizenship) if father_citizenship else _mid_y(mother_marker), minimum_height)
    mother_name = _person_name(blocks, _mid_y(mother_marker) - 30, _mid_y(mother_citizenship) if mother_citizenship else _mid_y(registration_marker), minimum_height)

    record_row_y = _mid_y(record_marker) - 35
    issue_row_y = _mid_y(issue_marker) - 12
    place_values = [
        block["text"].strip()
        for block in sorted(blocks, key=_mid_y)
        if _mid_y(place_marker) - 15 <= _mid_y(block) < record_row_y - 15
        and block["box"][0] > place_marker["box"][2] + 20
        and block is not place_marker
    ]
    registration_values = [
        block["text"].strip()
        for block in sorted(blocks, key=_mid_y)
        if _mid_y(registration_marker) - 30 <= _mid_y(block) < _mid_y(issue_marker) - 20
        and block is not registration_marker
        and not re.search(r"^НАЦ|ВЫДАЧИ|ВНОС|НАИМЕНОВАНИЕ", block["text"].upper())
        and len(block["text"].strip()) > 12
    ]
    record_number = _number_next_to_record(blocks, record_marker)
    series, number = _series_number(blocks)

    values: dict[str, str | None] = {key: None for key in BirthCertificateData.__annotations__}
    for role, name in (("Child", child_name), ("Father", father_name), ("Mother", mother_name)):
        for part, value in zip(("Surname", "GivenName", "Patronymic"), name):
            values[f"birthCertificate{role}{part}"] = value
    values.update({
        "birthCertificateChildDateOfBirth": birth_date,
        "birthCertificateChildPlaceOfBirth": ", ".join(value.rstrip(", ") for value in place_values) or None,
        "birthCertificateFatherCitizenship": _citizenship(father_citizenship),
        "birthCertificateMotherCitizenship": _citizenship(mother_citizenship),
        "birthCertificateFatherNationality": _nationality(blocks, father_citizenship, mother_marker),
        "birthCertificateMotherNationality": _nationality(blocks, mother_citizenship, registration_marker),
        "birthCertificateRegistrationDate": _split_date(_near(blocks, record_row_y, 35)),
        "birthCertificateRecordNumber": record_number,
        "birthCertificateRegistryOffice": " ".join(registration_values) or None,
        "birthCertificateIssueDate": _split_date(_near(blocks, issue_row_y, 40)),
        "birthCertificateSeries": series,
        "birthCertificateNumber": number,
    })
    return cast(BirthCertificateData, values)


def _find(blocks: list[OcrTextBlock], pattern: str) -> OcrTextBlock | None:
    matcher = re.compile(pattern, re.IGNORECASE)
    return next((block for block in blocks if matcher.search(block["text"].replace("ё", "е").upper())), None)


def _mid_y(block: OcrTextBlock) -> float:
    return (block["box"][1] + block["box"][3]) / 2


def _near(blocks: list[OcrTextBlock], y: float, distance: float) -> list[OcrTextBlock]:
    return [block for block in blocks if abs(_mid_y(block) - y) <= distance]


def _person_name(blocks: list[OcrTextBlock], top: float, bottom: float, minimum_height: float) -> tuple[str | None, str | None, str | None]:
    candidates = sorted(
        (block for block in blocks if top <= _mid_y(block) < bottom and block["box"][3] - block["box"][1] >= minimum_height),
        key=_mid_y,
    )
    surname_blocks = [
        block for block in candidates
        if SURNAME.fullmatch(block["text"].strip())
        and block["text"].strip().upper() not in {"ОТЕЦ", "МАТЬ"}
    ]
    given_blocks = [block for block in candidates if PERSON_NAME.fullmatch(block["text"].strip()) and len(block["text"].split()) == 2]
    for given in given_blocks:
        surname = next((block for block in reversed(surname_blocks) if 0 < _mid_y(given) - _mid_y(block) < 65), None)
        if surname:
            given_name, patronymic = given["text"].split()
            return surname["text"].strip().capitalize(), given_name, patronymic
    return None, None, None


def _visual_date(blocks: list[OcrTextBlock]) -> str | None:
    for block in blocks:
        match = VISUAL_DATE.search(block["text"])
        if match:
            try:
                return date(int(match.group(3)), int(match.group(2)), int(match.group(1))).isoformat()
            except ValueError:
                return None
    return None


def _split_date(blocks: list[OcrTextBlock]) -> str | None:
    years = {
        int(match.group(1))
        for block in blocks
        if (match := re.fullmatch(r"((?:19|20)\d{2})\s*[гr]?[.]?", block["text"].strip(), re.IGNORECASE))
    }
    days = {int(block["text"]) for block in blocks if re.fullmatch(r"\d{1,2}", block["text"].strip())}
    days.update(
        int(match.group(1))
        for block in blocks
        if (match := re.search(r"ВЫДАЧИ\s*[«\"']?\s*(\d{1,2})", block["text"], re.IGNORECASE))
    )
    months = {index for block in blocks for month, index in MONTHS.items() if month in block["text"].lower()}
    if len(years) != 1 or len(days) != 1 or len(months) != 1:
        return None
    try:
        return date(next(iter(years)), next(iter(months)), next(iter(days))).isoformat()
    except ValueError:
        return None


def _citizenship_block(blocks: list[OcrTextBlock], top: float, bottom: float) -> OcrTextBlock | None:
    return next((block for block in sorted(blocks, key=_mid_y) if top < _mid_y(block) < bottom and re.match(r"^граждан(?:ин|ка)\s+", block["text"], re.IGNORECASE)), None)


def _citizenship(block: OcrTextBlock | None) -> str | None:
    if not block:
        return None
    value = re.sub(r"^граждан(?:ин|ка)\s+", "", block["text"], flags=re.IGNORECASE).strip()
    if value.lower() == "россии":
        return "Россия"
    if re.fullmatch(r"российск\w+\s+федерац\w+", value.lower()):
        return "Российская Федерация"
    return value or None


def _nationality(blocks: list[OcrTextBlock], citizenship: OcrTextBlock | None, next_marker: OcrTextBlock) -> str | None:
    if citizenship is None:
        return None
    label = next(
        (block for block in sorted(blocks, key=_mid_y)
         if _mid_y(citizenship) < _mid_y(block) < _mid_y(next_marker)
         and block["text"].lower().startswith("нац")),
        None,
    )
    if label is None:
        return None
    candidates = {
        block["text"].strip().lower()
        for block in blocks
        if _mid_y(citizenship) < _mid_y(block) < _mid_y(label)
        and re.fullmatch(r"[а-яё-]{4,}", block["text"].strip(), re.IGNORECASE)
        and not block["text"].lower().startswith(("гражд", "нац"))
    }
    return next(iter(candidates)) if len(candidates) == 1 else None


def _number_next_to_record(blocks: list[OcrTextBlock], marker: OcrTextBlock) -> str | None:
    numbers = [
        block["text"].strip()
        for block in _near(blocks, _mid_y(marker), 30)
        if block["box"][0] >= marker["box"][2] and re.fullmatch(r"\d{1,6}", block["text"].strip())
    ]
    return numbers[0] if len(numbers) == 1 else None


def _series_number(blocks: list[OcrTextBlock]) -> tuple[str | None, str | None]:
    for block in sorted(blocks, key=_mid_y, reverse=True):
        match = SERIES_NUMBER.search(block["text"])
        if match:
            roman, suffix = match.group(1).upper().split("-", 1)
            return f"{roman}-{suffix.translate(LOOKALIKES)}", match.group(2)
    return None, None
