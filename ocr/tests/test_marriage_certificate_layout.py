from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certificate_parser import merge_marriage_certificate_pages


def block(text: str, x: int, y: int, width: int = 220, height: int = 40) -> dict[str, object]:
    return {"text": text, "box": (x, y, x + width, y + height)}


def marriage_blocks() -> list[dict[str, object]]:
    return [
        block("СВИДЕТЕЛЬСТВО", 790, 290, 620, 70),
        block("О ЗАКЛЮЧЕНИИ БРАКА", 675, 377, 850, 70),
        block("ПЕТРОВ", 1050, 556, 190, 50),
        block("(фамилия)", 1046, 609, 105, 21),
        block("Иван Сергеевич", 860, 614, 570, 70),
        block("(имя, отчество)", 950, 670, 300, 28),
        block("Российская Федерация", 877, 689, 535, 55),
        block("(гражданство)", 1027, 737, 140, 24),
        block("15", 326, 748, 66, 55),
        block("марта", 621, 760, 172, 45),
        block("1980", 1018, 756, 110, 50),
        block("pusskий", 1490, 759, 199, 55),
        block("(дата рождения)", 600, 799, 166, 27),
        block("Тверская область, г. Тверь", 559, 812, 1167, 72),
        block("(национальность)", 1458, 809, 175, 24),
        block("(место рождения)", 1014, 870, 172, 24),
        block("СИДОРОВА", 1006, 885, 273, 56),
        block("(фамилия)", 1041, 933, 110, 28),
        block("Мария Павловна", 835, 948, 615, 64),
        block("(имя, отчество)", 948, 1000, 296, 26),
        block("Российская Федерация", 875, 1017, 536, 61),
        block("(гражданство)", 1024, 1066, 141, 24),
        block("21", 324, 1078, 64, 52),
        block("марта", 620, 1090, 170, 42),
        block("1984", 1014, 1084, 111, 51),
        block("pycckaя", 1493, 1096, 189, 46),
        block("(дата рождения)", 602, 1129, 160, 24),
        block("Тверская область, г. Тверь", 557, 1139, 1169, 77),
        block("(национальность)", 1460, 1139, 168, 21),
        block("(место рождения)", 1007, 1197, 173, 27),
        block("заключили брак", 228, 1224, 294, 44),
        block("12 мая 2021 г.", 970, 1217, 338, 47),
        block("2021", 472, 1278, 107, 48),
        block("мая", 941, 1292, 132, 34),
        block("12", 1607, 1286, 62, 50),
        block("о чем", 231, 1298, 98, 28),
        block("составлена запись акта о заключении брака №", 225, 1357, 844, 47),
        block("120209720000100027004", 1335, 1353, 508, 46),
        block("После заключения брака присвоены фамилии:", 223, 1548, 840, 68),
        block("ПЕТРОВ", 1121, 1612, 187, 53),
        block("мужу", 225, 1629, 104, 43),
        block("Петрова", 1109, 1682, 209, 50),
        block("женe", 227, 1696, 95, 32),
        block("Место государственной регистрации", 225, 1751, 657, 55),
        block("97200001 Отдел ЗАГС администрации Тверского", 1008, 1750, 965, 57),
        block("(код и наименование органа)", 1164, 1795, 507, 33),
        block("муниципального района", 881, 1823, 511, 41),
        block("Место выдачи свидетельства", 229, 1950, 514, 47),
        block("12", 729, 2432, 65, 58),
        block("мая", 1047, 2441, 135, 42),
        block("2021", 1428, 2435, 115, 60),
        block("Дата выдачи«", 406, 2450, 271, 40),
        block("I-ΦP № 654321", 899, 2692, 367, 47),
    ]


class MarriageCertificateLayoutTest(unittest.TestCase):
    def test_reads_both_spouses_and_long_record_number(self) -> None:
        data = merge_marriage_certificate_pages([marriage_blocks()])
        self.assertEqual(data["marriageCertificateSpouse1SurnameBefore"], "Петров")
        self.assertEqual(data["marriageCertificateSpouse1GivenNameBefore"], "Иван")
        self.assertEqual(data["marriageCertificateSpouse1PatronymicBefore"], "Сергеевич")
        self.assertEqual(data["marriageCertificateSpouse1DateOfBirth"], "1980-03-15")
        self.assertEqual(data["marriageCertificateSpouse1PlaceOfBirth"], "Тверская область, г. Тверь")
        self.assertEqual(data["marriageCertificateSpouse1Citizenship"], "Российская Федерация")
        self.assertEqual(data["marriageCertificateSpouse1Nationality"], "русский")
        self.assertEqual(data["marriageCertificateSpouse1SurnameAfter"], "Петров")
        self.assertEqual(data["marriageCertificateSpouse2SurnameBefore"], "Сидорова")
        self.assertEqual(data["marriageCertificateSpouse2GivenNameBefore"], "Мария")
        self.assertEqual(data["marriageCertificateSpouse2PatronymicBefore"], "Павловна")
        self.assertEqual(data["marriageCertificateSpouse2DateOfBirth"], "1984-03-21")
        self.assertEqual(data["marriageCertificateSpouse2PlaceOfBirth"], "Тверская область, г. Тверь")
        self.assertEqual(data["marriageCertificateSpouse2Citizenship"], "Российская Федерация")
        self.assertEqual(data["marriageCertificateSpouse2Nationality"], "русская")
        self.assertEqual(data["marriageCertificateSpouse2SurnameAfter"], "Петрова")
        self.assertEqual(data["marriageCertificateMarriageDate"], "2021-05-12")
        self.assertEqual(data["marriageCertificateRecordDate"], "2021-05-12")
        self.assertEqual(data["marriageCertificateRecordNumber"], "120209720000100027004")
        self.assertEqual(data["marriageCertificateRegistryOffice"], "Отдел ЗАГС администрации Тверского муниципального района")
        self.assertEqual(data["marriageCertificateIssueDate"], "2021-05-12")
        self.assertEqual(data["marriageCertificateSeries"], "I-ФР")
        self.assertEqual(data["marriageCertificateNumber"], "654321")

    def test_ambiguous_date_does_not_fill_spouse_field(self) -> None:
        blocks = marriage_blocks()
        blocks.append(block("16", 400, 748, 60, 55))
        data = merge_marriage_certificate_pages([blocks])
        self.assertIsNone(data["marriageCertificateSpouse1DateOfBirth"])
        self.assertEqual(data["marriageCertificateSpouse2DateOfBirth"], "1984-03-21")


if __name__ == "__main__":
    unittest.main()
