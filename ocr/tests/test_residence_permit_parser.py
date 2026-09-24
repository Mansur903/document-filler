from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from passport_data_model import OcrTextBlock
from residence_permit_parser import (
    has_residence_permit_anchors,
    parse_residence_permit_data,
)


def block(text: str, box: tuple[int, int, int, int]) -> OcrTextBlock:
    return {"box": box, "text": text}


class ResidencePermitParserTest(unittest.TestCase):
    def test_extracts_all_fields_from_relative_layout(self) -> None:
        blocks = [
            block("خلفية عربية", (0, 0, 100, 20)),
            block("784200910498284", (300, 90, 470, 110)),
            block("U I D No.", (500, 90, 580, 110)),
            block("201 / 2024 / 3821949", (280, 130, 470, 150)),
            block("File No", (500, 130, 580, 150)),
            block("2027/08/28", (320, 180, 430, 200)),
            block("Expiry Date", (330, 205, 440, 225)),
            block("STUDENT / NOT ALLOWED TO WORK", (190, 250, 470, 272)),
            block("Profession", (500, 250, 590, 272)),
            block("ACME SERVICES LLC", (280, 290, 470, 312)),
            block("Employer", (500, 290, 580, 312)),
        ]

        self.assertTrue(has_residence_permit_anchors(blocks))
        self.assertEqual(
            parse_residence_permit_data(blocks),
            {
                "currentOccupation": "STUDENT / NOT ALLOWED TO WORK",
                "employer": "ACME SERVICES LLC",
                "residencepermitID": "784200910498284",
                "visaID": "201/2024/3821949",
                "visaValidUntil": "2027-08-28",
            },
        )

    def test_supports_inline_values_and_day_first_date(self) -> None:
        blocks = [
            block("UID No: 784200910498284", (0, 0, 250, 20)),
            block("File No 201/2024/3821949", (0, 30, 250, 50)),
            block("Expiry Date 28-08-2027", (0, 60, 250, 80)),
            block("Profession Engineer", (0, 90, 250, 110)),
            block("Employer Example Company", (0, 120, 250, 140)),
        ]

        data = parse_residence_permit_data(blocks)

        self.assertEqual(data["residencepermitID"], "784200910498284")
        self.assertEqual(data["visaID"], "201/2024/3821949")
        self.assertEqual(data["visaValidUntil"], "2027-08-28")
        self.assertEqual(data["currentOccupation"], "Engineer")
        self.assertEqual(data["employer"], "Example Company")

    def test_uses_unique_unlabelled_date_and_ignores_noise_before_employer_label(
        self,
    ) -> None:
        blocks = [
            block("UNITED ARAB EMIRATES", (155, 306, 503, 331)),
            block("784200910498284", (664, 398, 1052, 421)),
            block("201/2024/3821949", (624, 440, 1051, 467)),
            block("STUDENT /NOT ALLOWED TO WORK", (508, 582, 885, 607)),
            block("Profession", (907, 603, 1040, 620)),
            block("VYACHESLAV KONOVALOV", (591, 629, 870, 655)),
            block("4llsEmployer", (871, 646, 1045, 666)),
            block("2027/08/28", (388, 679, 493, 708)),
        ]

        data = parse_residence_permit_data(blocks)

        self.assertEqual(data["employer"], "VYACHESLAV KONOVALOV")
        self.assertEqual(data["visaValidUntil"], "2027-08-28")

    def test_returns_null_for_missing_ambiguous_or_invalid_values(self) -> None:
        blocks = [
            block("UID No", (500, 90, 580, 110)),
            block("12345678", (390, 90, 480, 110)),
            block("87654321", (390, 90, 480, 110)),
            block("File No", (500, 130, 580, 150)),
            block("Expiry Date 2027/99/99", (300, 180, 580, 200)),
            block("Profession", (500, 250, 590, 272)),
            block("Employer", (500, 290, 580, 312)),
        ]

        self.assertEqual(
            parse_residence_permit_data(blocks),
            {
                "currentOccupation": None,
                "employer": None,
                "residencepermitID": None,
                "visaID": None,
                "visaValidUntil": None,
            },
        )

    def test_does_not_guess_when_multiple_unlabelled_dates_exist(self) -> None:
        blocks = [
            block("2026/08/29", (100, 100, 220, 120)),
            block("2027/08/28", (100, 140, 220, 160)),
        ]

        self.assertIsNone(parse_residence_permit_data(blocks)["visaValidUntil"])


if __name__ == "__main__":
    unittest.main()
