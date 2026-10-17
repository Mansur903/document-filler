from pathlib import Path
import importlib.util
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mrz_parser import _calculate_check_digit
from recognize_passport import (
    _select_document_page,
    _read_rotated_side_numbers,
    _predict_internal_pdf_pages,
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
    def test_routes_internal_passport_without_changing_other_types(self) -> None:
        internal = _select_document_page(
            [result(["Фамилия", "ИВАНОВА", "Имя", "АННА"])],
            "russianInternalPassport",
        )
        self.assertIn("internalPassportSeries", internal)
        self.assertNotIn("numberOfTravelDocument", internal)
        self.assertEqual(_validate_document_type("russianInternalPassport"), "russianInternalPassport")

    def test_routes_passport_pages_without_changing_mrz_behavior(self) -> None:
        data = _select_document_page(
            [result(["Authority", "FMS 12345", *passport_mrz()])], "passport"
        )

        self.assertEqual(data["authority"], "FMS 12345")
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
        data = _select_document_page(
            [result(["Unrelated page"])], "uaeResidencePermit"
        )

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

    @unittest.skipUnless(importlib.util.find_spec("PIL") and importlib.util.find_spec("numpy"), "OCR image dependencies are unavailable")
    def test_reads_rotated_side_strip_only_for_internal_passport_page(self) -> None:
        from PIL import Image

        class FakeOcr:
            shapes: list[tuple[int, ...]] = []

            def predict(self, image: object) -> list[dict[str, object]]:
                self.shapes.append(image.shape)
                return [{"rec_texts": ["1234567890"]}]

        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "document.png"
            Image.new("RGB", (1000, 1200), "white").save(image_path)
            anchored = result(["Фамилия", "ИВАНОВА", "Имя", "АННА"])
            blocks = [
                {"text": text, "box": box}
                for text, box in zip(anchored["rec_texts"], anchored["rec_boxes"])
            ]
            ocr = FakeOcr()
            candidates = _read_rotated_side_numbers(ocr, image_path, [blocks])

        self.assertEqual(candidates, {0: ["1234567890", "1234567890"]})
        self.assertEqual(len(ocr.shapes), 2)
        self.assertTrue(all(shape[1] > shape[0] for shape in ocr.shapes))

    @unittest.skipUnless(importlib.util.find_spec("PIL") and importlib.util.find_spec("pypdfium2"), "OCR PDF dependencies are unavailable")
    def test_renders_only_anchored_pdf_page_for_side_retry(self) -> None:
        from PIL import Image

        class FakeOcr:
            calls = 0

            def predict(self, image: object) -> list[dict[str, object]]:
                self.calls += 1
                return [{"rec_texts": ["1234567890"]}]

        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "document.pdf"
            first = Image.new("RGB", (400, 500), "white")
            second = Image.new("RGB", (400, 500), "white")
            first.save(pdf_path, save_all=True, append_images=[second])
            anchored = result(["Фамилия", "ИВАНОВА", "Имя", "АННА"])
            blocks = [
                {"text": text, "box": box}
                for text, box in zip(anchored["rec_texts"], anchored["rec_boxes"])
            ]
            ocr = FakeOcr()
            candidates = _read_rotated_side_numbers(ocr, pdf_path, [[], blocks])

        self.assertEqual(candidates, {1: ["1234567890", "1234567890"]})
        self.assertEqual(ocr.calls, 2)

    @unittest.skipUnless(importlib.util.find_spec("PIL") and importlib.util.find_spec("pypdfium2"), "OCR PDF dependencies are unavailable")
    def test_renders_each_internal_pdf_page_before_ocr(self) -> None:
        from PIL import Image

        class FakeOcr:
            shapes: list[tuple[int, ...]] = []

            def predict(self, image: object) -> list[dict[str, object]]:
                self.shapes.append(image.shape)
                return [{"rec_texts": []}]

        with tempfile.TemporaryDirectory() as directory:
            pdf_path = Path(directory) / "document.pdf"
            first = Image.new("RGB", (400, 500), "white")
            second = Image.new("RGB", (400, 500), "white")
            first.save(pdf_path, save_all=True, append_images=[second])
            ocr = FakeOcr()
            results = _predict_internal_pdf_pages(ocr, pdf_path)

        self.assertEqual(len(results), 2)
        self.assertEqual(len(ocr.shapes), 2)
        self.assertTrue(all(shape[0] >= 500 for shape in ocr.shapes))


if __name__ == "__main__":
    unittest.main()
