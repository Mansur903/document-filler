from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mrz_parser import _calculate_check_digit, parse_passport_data
from passport_data_model import OcrTextBlock


def block(text: str, box: tuple[int, int, int, int]) -> OcrTextBlock:
    return {"box": box, "text": text}


def passport_mrz_blocks() -> list[OcrTextBlock]:
    document_number = "123456789"
    birth_date = "900101"
    expiry_date = "300101"
    line_one = "P<RUSIVANOV<<IVAN".ljust(44, "<")
    line_two = (
        f"{document_number}{_calculate_check_digit(document_number)}"
        f"RUS{birth_date}{_calculate_check_digit(birth_date)}"
        f"M{expiry_date}{_calculate_check_digit(expiry_date)}"
    ).ljust(44, "<")
    return [
        block(line_one, (0, 500, 500, 520)),
        block(line_two, (0, 530, 500, 550)),
    ]


class MrzParserAuthorityTest(unittest.TestCase):
    def test_returns_complete_contract_without_authority(self) -> None:
        data = parse_passport_data(passport_mrz_blocks())

        self.assertIn("authority", data)
        self.assertIsNone(data["authority"])
        self.assertEqual(data["numberOfTravelDocument"], "123456789")

    def test_extracts_inline_authority(self) -> None:
        blocks = [
            block("Authority  FMS 12345 ", (100, 100, 360, 120)),
            *passport_mrz_blocks(),
        ]

        self.assertEqual(parse_passport_data(blocks)["authority"], "FMS 12345")

    def test_extracts_authority_below_bilingual_label(self) -> None:
        blocks = [
            block("Authority", (100, 100, 420, 120)),
            block("Орган, выдавший документ", (100, 125, 420, 145)),
            block("MINISTRY  OF INTERNAL AFFAIRS", (100, 150, 420, 170)),
            *passport_mrz_blocks(),
        ]

        self.assertEqual(
            parse_passport_data(blocks)["authority"],
            "MINISTRY OF INTERNAL AFFAIRS",
        )

    def test_ignores_mixed_script_ocr_authority_label(self) -> None:
        blocks = [
            block(
                "Орган, выдавший документ/Аитhогiту",
                (100, 100, 420, 120),
            ),
            block("MVD 12345", (100, 125, 420, 145)),
            *passport_mrz_blocks(),
        ]

        self.assertEqual(parse_passport_data(blocks)["authority"], "MVD 12345")

    def test_rejects_nearby_date_as_authority(self) -> None:
        blocks = [
            block("Authority", (100, 100, 220, 120)),
            block("01.01.2020", (100, 130, 220, 150)),
            *passport_mrz_blocks(),
        ]

        self.assertIsNone(parse_passport_data(blocks)["authority"])

    def test_rejects_equally_ranked_authority_candidates(self) -> None:
        blocks = [
            block("Authority", (100, 100, 220, 120)),
            block("FMS 12345", (100, 130, 220, 150)),
            block("MVD 67890", (100, 130, 220, 150)),
            *passport_mrz_blocks(),
        ]

        data = parse_passport_data(blocks)

        self.assertIsNone(data["authority"])
        self.assertEqual(data["surname"], "Ivanov")


if __name__ == "__main__":
    unittest.main()
