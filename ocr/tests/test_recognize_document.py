from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mrz_parser import _calculate_check_digit
from recognize_passport import (
    _select_document_page,
    _validate_document_type,
    _validate_input_path,
)


def result(texts: list[str]) -> dict[str, object]:
    return {
        "rec_boxes": [
            (0, index * 30, 300, index * 30 + 20) for index in range(len(texts))
        ],
        "rec_texts": texts,
    }


def passport_mrz() -> list[str]:
    document_number = "123456789"
    birth_date = "900101"
    expiry_date = "300101"
    line_one = "P<RUSIVANOV<<IVAN".ljust(44, "<")
    line_two = (
        f"{document_number}{_calculate_check_digit(document_number)}"
        f"RUS{birth_date}{_calculate_check_digit(birth_date)}"
        f"M{expiry_date}{_calculate_check_digit(expiry_date)}"
    ).ljust(44, "<")
    return [line_one, line_two]


class RecognizeDocumentTest(unittest.TestCase):
    def test_routes_passport_pages_without_changing_mrz_behavior(self) -> None:
        data = _select_document_page([result(passport_mrz())], "passport")

        self.assertEqual(data["issuedByCountry"], "RUS")
        self.assertEqual(data["numberOfTravelDocument"], "123456789")

    def test_selects_first_residence_permit_page_with_anchors(self) -> None:
        pages = [
            result(["Unrelated page"]),
            result(
                [
                    "UID No: 784200910498284",
                    "File No: 201/2024/3821949",
                    "Expiry Date: 2027/08/28",
                    "Profession: Engineer",
                    "Employer: Example Company",
                ]
            ),
        ]

        data = _select_document_page(pages, "uaeResidencePermit")

        self.assertEqual(data["residencepermitID"], "784200910498284")
        self.assertEqual(data["visaValidUntil"], "2027-08-28")

    def test_returns_empty_permit_result_when_no_page_has_anchors(self) -> None:
        data = _select_document_page([result(["Unrelated page"])], "uaeResidencePermit")

        self.assertTrue(all(value is None for value in data.values()))

    def test_rejects_empty_ocr_result(self) -> None:
        with self.assertRaisesRegex(ValueError, "no document pages"):
            _select_document_page([], "uaeResidencePermit")

    def test_validates_type_and_png_extension(self) -> None:
        self.assertEqual(_validate_document_type("passport"), "passport")

        with self.assertRaisesRegex(ValueError, "document type"):
            _validate_document_type("unknown")

        with tempfile.TemporaryDirectory() as directory:
            png_path = Path(directory) / "permit.png"
            png_path.write_bytes(b"png")
            self.assertEqual(_validate_input_path(str(png_path)), png_path.resolve())

            unsupported_path = Path(directory) / "permit.bmp"
            unsupported_path.write_bytes(b"bmp")

            with self.assertRaisesRegex(ValueError, "JPG, JPEG, PNG, and PDF"):
                _validate_input_path(str(unsupported_path))


if __name__ == "__main__":
    unittest.main()
