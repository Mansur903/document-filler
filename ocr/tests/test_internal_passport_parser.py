from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from internal_passport_parser import (
    merge_internal_passport_pages,
    page_anchor_groups,
    parse_internal_passport_data,
)
from passport_data_model import OcrTextBlock


def block(text: str, x: int, y: int, width: int = 170) -> OcrTextBlock:
    return {"box": (x, y, x + width, y + 22), "text": text}


def upper_page() -> list[OcrTextBlock]:
    return [
        block("Паспорт выдан", 100, 100, 130),
        block("ОТДЕЛОМ МВД", 270, 70, 330),
        block("ПО ЦЕНТРАЛЬНОМУ РАЙОНУ", 270, 115, 430),
        block("Дата выдачи", 100, 250, 120),
        block("11.02.2019", 240, 250, 140),
        block("Код подразделения", 480, 250, 190),
        block("123-456", 700, 250, 130),
        block("12", 900, 160, 65),
        block("34", 900, 220, 65),
        block("567890", 900, 280, 65),
    ]


def lower_page() -> list[OcrTextBlock]:
    return [
        block("Фамилия", 300, 700, 100),
        block("ИВАНОВА", 550, 700, 170),
        block("Имя", 300, 750, 75),
        block("АННА", 550, 750, 100),
        block("Отчество", 300, 800, 115),
        block("СЕРГЕЕВНА", 550, 800, 200),
        block("Пол", 300, 850, 70),
        block("ЖЕН.", 390, 850, 80),
        block("Дата рождения", 490, 850, 170),
        block("03.04.1992", 680, 850, 160),
        block("Место рождения", 300, 930, 170),
        block("ГОРОД ПРИМЕРСК", 550, 930, 300),
        block("ПРИМЕРСКАЯ ОБЛАСТЬ", 550, 970, 350),
        block("12", 900, 700, 65),
        block("34", 900, 760, 65),
        block("567890", 900, 820, 65),
    ]


class InternalPassportParserTest(unittest.TestCase):
    def test_parses_complete_spread(self) -> None:
        data = parse_internal_passport_data(upper_page() + lower_page())
        self.assertEqual(data["surname"], "ИВАНОВА")
        self.assertEqual(data["givenName"], "АННА")
        self.assertEqual(data["patronymic"], "СЕРГЕЕВНА")
        self.assertEqual(data["sex"], "F")
        self.assertEqual(data["dateOfBirth"], "1992-04-03")
        self.assertEqual(data["placeOfBirth"], "ГОРОД ПРИМЕРСК ПРИМЕРСКАЯ ОБЛАСТЬ")
        self.assertEqual(data["dateOfIssue"], "2019-02-11")
        self.assertEqual(data["subdivisionCode"], "123-456")
        self.assertEqual(data["authority"], "ОТДЕЛОМ МВД ПО ЦЕНТРАЛЬНОМУ РАЙОНУ")
        self.assertEqual(data["internalPassportSeries"], "1234")
        self.assertEqual(data["internalPassportNumber"], "567890")
        self.assertNotIn("numberOfTravelDocument", data)
        self.assertNotIn("validUntil", data)

    def test_keeps_other_fields_when_patronymic_is_missing(self) -> None:
        blocks = [item for item in lower_page() if item["text"] != "СЕРГЕЕВНА"]
        data = parse_internal_passport_data(blocks)
        self.assertIsNone(data["patronymic"])
        self.assertEqual(data["givenName"], "АННА")

    def test_accepts_common_mixed_script_label_errors(self) -> None:
        blocks = [
            {**item, "text": "Hlox"} if item["text"] == "Пол" else item
            for item in lower_page()
        ]
        blocks = [
            {**item, "text": "ЖEH."} if item["text"] == "ЖЕН." else item
            for item in blocks
        ]
        self.assertEqual(parse_internal_passport_data(blocks)["sex"], "F")

    def test_rejects_invalid_dates_and_conflicting_side_numbers(self) -> None:
        blocks = upper_page() + lower_page()
        blocks = [
            {**item, "text": "31.02.2019"} if item["text"] == "11.02.2019" else item
            for item in blocks
        ]
        blocks.append(block("9999999999", 900, 1080, 65))
        data = parse_internal_passport_data(blocks)
        self.assertIsNone(data["dateOfIssue"])
        self.assertIsNone(data["internalPassportSeries"])
        self.assertIsNone(data["internalPassportNumber"])
        self.assertEqual(data["subdivisionCode"], "123-456")

    def test_selects_split_pages_and_ignores_unrelated_page(self) -> None:
        pages = [[block("Unrelated document", 10, 10)], upper_page(), lower_page()]
        self.assertEqual(page_anchor_groups(pages[0]), (False, False))
        data = merge_internal_passport_pages(pages)
        self.assertEqual(data["surname"], "ИВАНОВА")
        self.assertEqual(data["authority"], "ОТДЕЛОМ МВД ПО ЦЕНТРАЛЬНОМУ РАЙОНУ")

    def test_does_not_merge_conflicting_pages(self) -> None:
        conflicting = [
            {**item, "text": "999999"} if item["text"] == "567890" else item
            for item in lower_page()
        ]
        data = merge_internal_passport_pages([upper_page(), conflicting])
        self.assertIsNone(data["authority"])
        self.assertEqual(data["surname"], "ИВАНОВА")

    def test_rejects_foreign_passport_mrz_even_with_similar_labels(self) -> None:
        blocks = lower_page() + [block("P<RUSIVANOVA<<ANNA", 20, 1100, 500)]
        self.assertEqual(page_anchor_groups(blocks), (False, False))
        self.assertTrue(all(value is None for value in parse_internal_passport_data(blocks).values()))


if __name__ == "__main__":
    unittest.main()
