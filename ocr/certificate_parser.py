"""Parses Russian civil certificates from positioned OCR text blocks."""

from __future__ import annotations

from datetime import date
import re
from typing import cast

from birth_certificate_layout import parse_birth_certificate_layout
from marriage_certificate_layout import parse_marriage_certificate_layout
from passport_data_model import (
    BirthCertificateData,
    MarriageCertificateData,
    OcrTextBlock,
)


DATE_PATTERN = re.compile(r"(?<!\d)(\d{1,2})[.\-/\s]+(\d{1,2})[.\-/\s]+(\d{4})(?!\d)")
ISO_DATE_PATTERN = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
RUSSIAN_DATE_PATTERN = re.compile(
    r"(?<!\d)(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})(?!\d)",
    re.IGNORECASE,
)
MONTHS = {
    month: index for index, month in enumerate(
        ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"),
        start=1,
    )
}
SERIES_NUMBER_PATTERN = re.compile(
    r"СЕРИ[ЯИ]\s*[:№]?\s*([IVXА-ЯA-Z0-9-]{2,12})\s*(?:№|НОМЕР)\s*(\d{4,10})",
    re.IGNORECASE,
)
NAME_PATTERN = re.compile(r"^[А-ЯЁ][А-ЯЁ\-]+(?:\s+[А-ЯЁ][А-ЯЁ\-]+){1,2}$", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"(?:№|НОМЕР)\s*([0-9]{1,12})", re.IGNORECASE)
FATHER_MARKER = re.compile(r"^ОТЕЦ\b", re.IGNORECASE)
MOTHER_MARKER = re.compile(r"^МАТЬ\b", re.IGNORECASE)
SPOUSE1_MARKER = re.compile(r"^(?:ОН\b|ГРАЖДАНИН\b|СУПРУГ\s*1\b)", re.IGNORECASE)
SPOUSE2_MARKER = re.compile(r"^(?:ОНА\b|ГРАЖДАНКА\b|СУПРУГ\s*2\b)", re.IGNORECASE)
RECORD_MARKER = re.compile(r"(?:ЗАПИС[ЬИ]\s+АКТА|АКТОВАЯ\s+ЗАПИСЬ)", re.IGNORECASE)
LABEL_MARKER = re.compile(
    r"^(?:ФАМИЛИЯ|ИМЯ|ОТЧЕСТВО|ДАТА|МЕСТО|ГРАЖДАНСТВО|НАЦИОНАЛЬНОСТЬ|"
    r"СЕРИЯ|НОМЕР|ЗАГС|ОРГАН|ЗАПИСЬ|СУПРУГ|ОТЕЦ|МАТЬ)\b",
    re.IGNORECASE,
)
LABEL_LOOKALIKES = str.maketrans({
    "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "I": "И",
    "K": "К", "M": "М", "N": "И", "O": "О", "P": "Р", "T": "Т", "X": "Х", "Y": "У",
})


def _label_text(value: str) -> str:
    return value.upper().replace("Ё", "Е").translate(LABEL_LOOKALIKES)


def empty_birth_certificate_data() -> BirthCertificateData:
    return cast(BirthCertificateData, {
        key: None for key in BirthCertificateData.__annotations__
    })


def empty_marriage_certificate_data() -> MarriageCertificateData:
    return cast(MarriageCertificateData, {
        key: None for key in MarriageCertificateData.__annotations__
    })


def merge_birth_certificate_pages(pages: list[list[OcrTextBlock]]) -> BirthCertificateData:
    return cast(BirthCertificateData, _merge_pages(pages, "birth"))


def merge_marriage_certificate_pages(pages: list[list[OcrTextBlock]]) -> MarriageCertificateData:
    return cast(MarriageCertificateData, _merge_pages(pages, "marriage"))


def _merge_pages(pages: list[list[OcrTextBlock]], kind: str) -> dict[str, str | None]:
    merged: dict[str, str | None] = (
        empty_birth_certificate_data() if kind == "birth" else empty_marriage_certificate_data()
    )
    found = False
    conflicts: set[str] = set()

    for blocks in pages:
        lines = _ordered_lines(blocks)
        if not _has_anchors(lines, kind):
            continue
        found = True
        parsed = (
            parse_birth_certificate_layout(blocks) or _parse_birth(lines)
            if kind == "birth" else parse_marriage_certificate_layout(blocks) or _parse_marriage(lines)
        )
        for key, value in parsed.items():
            if value is None or key in conflicts:
                continue
            if merged[key] is not None and merged[key] != value:
                merged[key] = None
                conflicts.add(key)
            else:
                merged[key] = value

    if not found:
        raise ValueError("No matching civil certificate was found.")
    return merged


def _ordered_lines(blocks: list[OcrTextBlock]) -> list[str]:
    ordered = sorted(blocks, key=lambda block: (block["box"][1], block["box"][0]))
    return [re.sub(r"\s+", " ", block["text"]).strip() for block in ordered if block["text"].strip()]


def _has_anchors(lines: list[str], kind: str) -> bool:
    text = _label_text(" ".join(lines))
    if kind == "birth":
        return bool(re.search(r"СВИДЕТЕЛЬСТВО\s+О\s+РОЖДЕНИИ", text))
    return bool(re.search(r"СВИДЕТЕЛЬСТВО\s+О\s+ЗАКЛЮЧЕНИИ\s+БРАКА", text))


def _section(lines: list[str], start: re.Pattern[str], end: re.Pattern[str] | None = None) -> list[str]:
    indexes = [index for index, line in enumerate(lines) if start.search(_label_text(line))]
    if len(indexes) != 1:
        return []
    first = indexes[0] + 1
    last = next((index for index in range(first, len(lines)) if end and end.search(_label_text(lines[index]))), len(lines))
    return lines[first:last]


def _field(lines: list[str], pattern: str) -> str | None:
    label = re.compile(pattern, re.IGNORECASE)
    matches: list[str] = []
    for index, line in enumerate(lines):
        found = label.match(_label_text(line))
        if not found:
            continue
        tail = line[found.end():].strip(" :—–-")
        if not tail and index + 1 < len(lines) and not LABEL_MARKER.match(_label_text(lines[index + 1])):
            tail = lines[index + 1].strip(" :—–-")
        if tail:
            matches.append(tail)
    return matches[0] if len(set(matches)) == 1 else None


def _name_fields(lines: list[str], prefix: str, suffix: str = "") -> dict[str, str | None]:
    before = r"(?:\s+ДО\s+ЗАКЛЮЧЕНИЯ\s+БРАКА)?" if suffix else ""
    parts = {
        "Surname": _field(lines, rf"^ФАМИЛИЯ(?!\s+ПОСЛЕ){before}\s*"),
        "GivenName": _field(lines, r"^ИМЯ\s*"),
        "Patronymic": _field(lines, r"^ОТЧЕСТВО\s*"),
    }
    if not any(parts.values()):
        candidate = next((line for line in lines[:5] if NAME_PATTERN.fullmatch(line) and "СВИДЕТЕЛЬСТВО" not in line.upper()), None)
        if candidate:
            tokens = candidate.split()
            parts = {
                "Surname": tokens[0],
                "GivenName": tokens[1],
                "Patronymic": tokens[2] if len(tokens) == 3 else None,
            }
    return {f"{prefix}{part}{suffix}": value for part, value in parts.items()}


def _date(value: str | None) -> str | None:
    if not value:
        return None
    iso = ISO_DATE_PATTERN.search(value)
    visual = DATE_PATTERN.search(value)
    russian = RUSSIAN_DATE_PATTERN.search(value)
    if iso:
        year, month, day = map(int, iso.groups())
    elif visual:
        day, month, year = map(int, visual.groups())
    elif russian:
        day = int(russian.group(1))
        month = MONTHS[russian.group(2).lower()]
        year = int(russian.group(3))
    else:
        return None
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _date_field(lines: list[str], pattern: str) -> str | None:
    return _date(_field(lines, pattern))


def _context_date(lines: list[str], pattern: str) -> str | None:
    label = re.compile(pattern, re.IGNORECASE)
    candidates = {_date(line) for line in lines if label.search(_label_text(line))} - {None}
    return next(iter(candidates)) if len(candidates) == 1 else None


def _number(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"\d{1,12}", value)
    return match.group() if match else None


def _certificate_numbers(lines: list[str]) -> tuple[str | None, str | None]:
    for line in lines:
        match = SERIES_NUMBER_PATTERN.search(line)
        if match:
            return _normalize_series(match.group(1)), match.group(2)
    series = _field(lines, r"^СЕРИ[ЯИ]\s*")
    number = _field(lines, r"^(?:НОМЕР|№)\s+(?:СВИДЕТЕЛЬСТВА\s*)?")
    return _normalize_series(series), _number(number)


def _normalize_series(value: str | None) -> str | None:
    if not value:
        return None
    series = value.strip().upper()
    roman, separator, suffix = series.rpartition("-")
    if separator and re.fullmatch(r"[IVX]+", roman) and re.fullmatch(r"[А-ЯA-Z]+", suffix):
        return f"{roman}-{suffix.translate(LABEL_LOOKALIKES)}"
    return series


def _record_number(lines: list[str]) -> str | None:
    candidates: set[str] = set()
    for index, line in enumerate(lines):
        if not RECORD_MARKER.search(_label_text(line)):
            continue
        match = NUMBER_PATTERN.search(line)
        if not match and index + 1 < len(lines):
            match = NUMBER_PATTERN.search(lines[index + 1])
        if match:
            candidates.add(match.group(1))
    return next(iter(candidates)) if len(candidates) == 1 else None


def _registry_office(lines: list[str]) -> str | None:
    return _field(lines, r"^(?:НАИМЕНОВАНИЕ\s+ОРГАНА\s+ЗАГС|ОРГАН\s+ЗАГС|ЗАГС)\s*")


def _parse_birth(lines: list[str]) -> BirthCertificateData:
    result = empty_birth_certificate_data()
    father_start = next((index for index, line in enumerate(lines) if FATHER_MARKER.match(_label_text(line))), len(lines))
    child = lines[:father_start]
    father = _section(lines, FATHER_MARKER, MOTHER_MARKER)
    mother = _section(lines, MOTHER_MARKER, RECORD_MARKER)

    result.update(_name_fields(child, "birthCertificateChild"))
    result["birthCertificateChildDateOfBirth"] = _date_field(child, r"^(?:ДАТА\s+РОЖДЕНИЯ|РОДИЛ[САЬ][ЯЬ]?)\s*")
    result["birthCertificateChildPlaceOfBirth"] = _field(child, r"^МЕСТО\s+РОЖДЕНИЯ\s*")
    for role, section in (("Father", father), ("Mother", mother)):
        prefix = f"birthCertificate{role}"
        result.update(_name_fields(section, prefix))
        result[f"{prefix}DateOfBirth"] = _date_field(section, r"^(?:ДАТА\s+РОЖДЕНИЯ|РОДИЛ[САЬ][ЯЬ]?)\s*")
        result[f"{prefix}Citizenship"] = _field(section, r"^ГРАЖДАНСТВО\s*")
        result[f"{prefix}Nationality"] = _field(section, r"^НАЦИОНАЛЬНОСТЬ\s*")
    result["birthCertificateRegistrationDate"] = _date_field(lines, r"^(?:ДАТА\s+ГОСУДАРСТВЕННОЙ\s+РЕГИСТРАЦИИ|ДАТА\s+СОСТАВЛЕНИЯ\s+АКТОВОЙ\s+ЗАПИСИ)\s*") or _context_date(lines, r"ЗАПИС[ЬИ]\s+АКТА\s+О\s+РОЖДЕНИИ")
    result["birthCertificateRecordNumber"] = _record_number(lines)
    result["birthCertificateRegistryOffice"] = _registry_office(lines)
    result["birthCertificateIssueDate"] = _date_field(lines, r"^(?:ДАТА\s+ВЫДАЧИ|ВЫДАНО)\s*")
    result["birthCertificateSeries"], result["birthCertificateNumber"] = _certificate_numbers(lines)
    return result


def _parse_marriage(lines: list[str]) -> MarriageCertificateData:
    result = empty_marriage_certificate_data()
    first = _section(lines, SPOUSE1_MARKER, SPOUSE2_MARKER)
    second = _section(lines, SPOUSE2_MARKER, RECORD_MARKER)
    for role, section in (("Spouse1", first), ("Spouse2", second)):
        prefix = f"marriageCertificate{role}"
        result.update(_name_fields(section, prefix, "Before"))
        result[f"{prefix}DateOfBirth"] = _date_field(section, r"^ДАТА\s+РОЖДЕНИЯ\s*")
        result[f"{prefix}PlaceOfBirth"] = _field(section, r"^МЕСТО\s+РОЖДЕНИЯ\s*")
        result[f"{prefix}Citizenship"] = _field(section, r"^ГРАЖДАНСТВО\s*")
        result[f"{prefix}Nationality"] = _field(section, r"^НАЦИОНАЛЬНОСТЬ\s*")
        result[f"{prefix}SurnameAfter"] = _field(section, r"^ФАМИЛИЯ\s+ПОСЛЕ\s+ЗАКЛЮЧЕНИЯ\s+БРАКА\s*")
    result["marriageCertificateMarriageDate"] = _date_field(lines, r"^ДАТА\s+ЗАКЛЮЧЕНИЯ\s+БРАКА\s*") or _context_date(lines, r"ЗАКЛЮЧИЛИ\s+БРАК")
    result["marriageCertificateRecordDate"] = _date_field(lines, r"^ДАТА\s+СОСТАВЛЕНИЯ\s+АКТОВОЙ\s+ЗАПИСИ\s*") or _context_date(lines, r"СОСТАВЛЕНА\s+ЗАПИСЬ\s+АКТА")
    result["marriageCertificateRecordNumber"] = _record_number(lines)
    result["marriageCertificateRegistryOffice"] = _registry_office(lines)
    result["marriageCertificateIssueDate"] = _date_field(lines, r"^(?:ДАТА\s+ВЫДАЧИ|ВЫДАНО)\s*")
    result["marriageCertificateSeries"], result["marriageCertificateNumber"] = _certificate_numbers(lines)
    return result
