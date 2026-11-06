from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

from PIL import Image


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certificate_parser import merge_birth_certificate_pages
from recognize_passport import _retry_birth_missing_names, _retry_birth_mother_surname


def block(text: str, x: int, y: int, width: int = 220, height: int = 28) -> dict[str, object]:
    return {"text": text, "box": (x, y, x + width, y + height)}


def certificate_blocks() -> list[dict[str, object]]:
    return [
        block("СВИДЕТЕЛЬСТВО", 550, 270, 330, 40),
        block("О РОЖДЕНИИ", 580, 310, 280, 40),
        block("Соколова", 650, 415, 150),
        block("фамилия", 690, 445, 70, 14),
        block("Мария Павловна", 585, 455, 260),
        block("05/01/2014", 675, 485, 130),
        block("родился(лась)", 320, 495, 140),
        block("г. Тула", 770, 590, 160),
        block("место рождения", 320, 600, 160),
        block("Тульская область", 575, 625, 290),
        block("Россия", 675, 660, 90),
        block("2014", 450, 695, 65),
        block("января", 685, 695, 125),
        block("10", 990, 695, 40),
        block("2345", 710, 730, 70),
        block("составлена запись акта о рождении №", 320, 735, 375),
        block("Отец", 320, 770, 60),
        block("Соколов", 685, 765, 140),
        block("Павел Иванович", 565, 795, 320),
        block("гражданин России", 600, 825, 250),
        block("Мать", 320, 910, 60),
        block("околова", 700, 905, 120),
        block("Елена Сергеевна", 590, 940, 275),
        block("гражданка России", 600, 970, 250),
        block("национальность (вносится по желанию матери)", 590, 1035, 290, 18),
        block("Отдел записи актов", 720, 1040, 370),
        block("Место государственной регистрации", 315, 1058, 365),
        block("гражданского состояния Тульской области", 390, 1080, 660),
        block("по Центральному району г. Тулы", 520, 1110, 420),
        block("2014", 1080, 1160, 70),
        block("января", 820, 1170, 130),
        block("12", 650, 1175, 40),
        block("выдачи «", 550, 1185, 100),
        block("III-KB N 123456", 620, 1345, 220),
    ]


class BirthCertificateLayoutTest(unittest.TestCase):
    def test_reads_positional_fields_and_split_dates(self) -> None:
        data = merge_birth_certificate_pages([certificate_blocks()])
        self.assertEqual(data["birthCertificateChildSurname"], "Соколова")
        self.assertEqual(data["birthCertificateChildGivenName"], "Мария")
        self.assertEqual(data["birthCertificateChildPatronymic"], "Павловна")
        self.assertEqual(data["birthCertificateChildDateOfBirth"], "2014-01-05")
        self.assertEqual(data["birthCertificateChildPlaceOfBirth"], "г. Тула, Тульская область, Россия")
        self.assertEqual(data["birthCertificateFatherSurname"], "Соколов")
        self.assertEqual(data["birthCertificateFatherGivenName"], "Павел")
        self.assertEqual(data["birthCertificateMotherSurname"], "Околова")
        self.assertEqual(data["birthCertificateMotherGivenName"], "Елена")
        self.assertEqual(data["birthCertificateFatherCitizenship"], "Россия")
        self.assertEqual(data["birthCertificateMotherCitizenship"], "Россия")
        self.assertIsNone(data["birthCertificateFatherDateOfBirth"])
        self.assertIsNone(data["birthCertificateMotherNationality"])
        self.assertEqual(data["birthCertificateRegistrationDate"], "2014-01-10")
        self.assertEqual(data["birthCertificateRecordNumber"], "2345")
        self.assertEqual(data["birthCertificateRegistryOffice"], "Отдел записи актов гражданского состояния Тульской области по Центральному району г. Тулы")
        self.assertEqual(data["birthCertificateIssueDate"], "2014-01-12")
        self.assertEqual(data["birthCertificateSeries"], "III-КВ")
        self.assertEqual(data["birthCertificateNumber"], "123456")

    def test_ambiguous_split_date_stays_empty(self) -> None:
        blocks = certificate_blocks()
        blocks.append(block("11", 930, 695, 40))
        data = merge_birth_certificate_pages([blocks])
        self.assertIsNone(data["birthCertificateRegistrationDate"])
        self.assertEqual(data["birthCertificateRecordNumber"], "2345")

    def test_optional_nationalities_and_inline_issue_day(self) -> None:
        blocks = certificate_blocks()
        blocks.extend([
            block("татарин", 690, 865, 120),
            block("национальность (по желанию отца)", 590, 890, 320, 18),
            block("русская", 690, 1010, 120),
            block("национальность (по желанию матери)", 590, 1030, 320, 18),
        ])
        blocks = [item for item in blocks if item["text"] != "12"]
        next(item for item in blocks if item["text"] == "выдачи «")["text"] = "Дата выдачи 12"
        next(item for item in blocks if item["text"] == "2014" and item["box"][1] > 1100)["text"] = "2014г."
        data = merge_birth_certificate_pages([blocks])
        self.assertEqual(data["birthCertificateFatherNationality"], "татарин")
        self.assertEqual(data["birthCertificateMotherNationality"], "русская")
        self.assertEqual(data["birthCertificateIssueDate"], "2014-01-12")

    def test_retries_mixed_script_names_from_their_own_crops(self) -> None:
        blocks = certificate_blocks()
        next(item for item in blocks if item["text"] == "Мария Павловна")["text"] = "Мaрия Пaвловна"
        next(item for item in blocks if item["text"] == "Павел Иванович")["text"] = "Пaвел Ивaнович"
        result = {"rec_texts": [item["text"] for item in blocks], "rec_boxes": [item["box"] for item in blocks]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "certificate.png"
            Image.new("RGB", (1300, 1500), "white").save(path)
            ocr = Mock()
            ocr.predict.side_effect = [
                [{"rec_texts": ["Мария Павловна"]}],
                [{"rec_texts": ["Павел Иванович"]}],
            ]
            parsed = merge_birth_certificate_pages([blocks])
            recovered = _retry_birth_missing_names(ocr, path, [result], parsed)
            self.assertEqual(recovered["birthCertificateChildSurname"], "Соколова")
            self.assertEqual(recovered["birthCertificateChildGivenName"], "Мария")
            self.assertEqual(recovered["birthCertificateFatherSurname"], "Соколов")
            self.assertEqual(recovered["birthCertificateFatherGivenName"], "Павел")

    def test_retries_maternal_surname_without_guessing_from_other_people(self) -> None:
        blocks = certificate_blocks()
        result = {"rec_texts": [item["text"] for item in blocks], "rec_boxes": [item["box"] for item in blocks]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "certificate.png"
            Image.new("RGB", (1300, 1500), "white").save(path)

            ocr = Mock()
            ocr.predict.return_value = [{"rec_texts": ["Соколова"]}]
            parsed = merge_birth_certificate_pages([blocks])
            recovered = _retry_birth_mother_surname(ocr, path, [result], parsed)
            self.assertEqual(recovered["birthCertificateMotherSurname"], "Соколова")

            ocr.predict.return_value = [{"rec_texts": ["Коколова"]}]
            parsed = merge_birth_certificate_pages([blocks])
            unchanged = _retry_birth_mother_surname(ocr, path, [result], parsed)
            self.assertEqual(unchanged["birthCertificateMotherSurname"], "Околова")


if __name__ == "__main__":
    unittest.main()
