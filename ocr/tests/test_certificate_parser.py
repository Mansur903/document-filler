from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from certificate_parser import merge_birth_certificate_pages, merge_marriage_certificate_pages
from passport_data_model import BirthCertificateData, MarriageCertificateData


def blocks(*texts: str) -> list[dict[str, object]]:
    return [
        {"text": text, "box": (0, index * 30, 400, index * 30 + 20)}
        for index, text in enumerate(texts)
    ]


def birth_page() -> list[dict[str, object]]:
    return blocks(
        "СВИДЕТЕЛЬСТВО О РОЖДЕНИИ",
        "Фамилия Петров", "Имя Алексей", "Отчество Игоревич",
        "Дата рождения 12.03.2018", "Место рождения Москва",
        "Отец", "Фамилия Петров", "Имя Игорь", "Отчество Сергеевич",
        "Дата рождения 01.02.1989", "Гражданство Российская Федерация",
        "Национальность русский",
        "Мать", "Фамилия Петрова", "Имя Анна", "Отчество Ивановна",
        "Дата рождения 21.04.1990", "Гражданство Российская Федерация",
        "Дата государственной регистрации 15.03.2018",
        "Запись акта о рождении № 321", "ЗАГС Тверского района Москвы",
        "Дата выдачи 16.03.2018", "Серия IV-АН № 654321",
    )


def marriage_page() -> list[dict[str, object]]:
    return blocks(
        "СВИДЕТЕЛЬСТВО О ЗАКЛЮЧЕНИИ БРАКА", "Он",
        "Фамилия до заключения брака Иванов", "Имя Павел", "Отчество Ильич",
        "Дата рождения 02.05.1988", "Место рождения Тверь",
        "Гражданство Российская Федерация", "Национальность русский",
        "Фамилия после заключения брака Иванов", "Она",
        "Фамилия до заключения брака Смирнова", "Имя Мария", "Отчество Павловна",
        "Дата рождения 03.06.1991", "Место рождения Москва",
        "Гражданство Российская Федерация", "Национальность русская",
        "Фамилия после заключения брака Иванова",
        "Дата заключения брака 14.07.2022",
        "Запись акта о заключении брака № 555",
        "Дата составления актовой записи 15.07.2022",
        "ЗАГС города Москвы", "Дата выдачи 16.07.2022",
        "Серия III-АН № 123456",
    )


class CertificateParserTest(unittest.TestCase):
    def test_birth_fields_and_missing_nationality(self) -> None:
        data = merge_birth_certificate_pages([birth_page()])
        self.assertEqual(set(data), set(BirthCertificateData.__annotations__))
        self.assertEqual(data["birthCertificateChildSurname"], "Петров")
        self.assertEqual(data["birthCertificateFatherGivenName"], "Игорь")
        self.assertEqual(data["birthCertificateMotherGivenName"], "Анна")
        self.assertEqual(data["birthCertificateMotherNationality"], None)
        self.assertEqual(data["birthCertificateRegistrationDate"], "2018-03-15")
        self.assertEqual(data["birthCertificateRecordNumber"], "321")
        self.assertEqual(data["birthCertificateSeries"], "IV-АН")
        self.assertEqual(data["birthCertificateNumber"], "654321")

    def test_marriage_fields_and_distinct_dates(self) -> None:
        data = merge_marriage_certificate_pages([marriage_page()])
        self.assertEqual(set(data), set(MarriageCertificateData.__annotations__))
        self.assertEqual(data["marriageCertificateSpouse1SurnameBefore"], "Иванов")
        self.assertEqual(data["marriageCertificateSpouse1SurnameAfter"], "Иванов")
        self.assertEqual(data["marriageCertificateSpouse2SurnameBefore"], "Смирнова")
        self.assertEqual(data["marriageCertificateSpouse2SurnameAfter"], "Иванова")
        self.assertEqual(data["marriageCertificateMarriageDate"], "2022-07-14")
        self.assertEqual(data["marriageCertificateRecordDate"], "2022-07-15")
        self.assertEqual(data["marriageCertificateRecordNumber"], "555")
        self.assertEqual(data["marriageCertificateNumber"], "123456")

    def test_rejects_unrelated_page_and_conflicting_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "No matching"):
            merge_birth_certificate_pages([blocks("Passport", "Other")])
        other = birth_page()
        other[1]["text"] = "Фамилия Сидоров"
        data = merge_birth_certificate_pages([birth_page(), other])
        self.assertIsNone(data["birthCertificateChildSurname"])
        self.assertEqual(data["birthCertificateNumber"], "654321")

    def test_invalid_date_does_not_replace_other_fields(self) -> None:
        page = birth_page()
        page[4]["text"] = "Дата рождения 31.02.2018"
        data = merge_birth_certificate_pages([page])
        self.assertIsNone(data["birthCertificateChildDateOfBirth"])
        self.assertEqual(data["birthCertificateChildGivenName"], "Алексей")

    def test_russian_months_and_mixed_script_labels(self) -> None:
        page = birth_page()
        page[0]["text"] = "CВИДЕТЕЛЬСТВО О РОЖДЕНИИ"
        page[4]["text"] = "Дата рождения 12 марта 2018 года"
        page[6]["text"] = "ОTЕЦ"
        page[7]["text"] = "ФAМИЛИЯ Петров"
        data = merge_birth_certificate_pages([page])
        self.assertEqual(data["birthCertificateChildDateOfBirth"], "2018-03-12")
        self.assertEqual(data["birthCertificateFatherSurname"], "Петров")

    def test_latin_lookalikes_in_series_keep_roman_prefix(self) -> None:
        page = birth_page()
        page[-1]["text"] = "Серия IV-AH № 654321"
        data = merge_birth_certificate_pages([page])
        self.assertEqual(data["birthCertificateSeries"], "IV-АН")

    def test_marriage_conflict_does_not_assign_another_spouses_value(self) -> None:
        page = marriage_page()
        page[11]["text"] = "Фамилия до заключения брака"
        page[12]["text"] = "Имя Мария"
        data = merge_marriage_certificate_pages([page])
        self.assertIsNone(data["marriageCertificateSpouse2SurnameBefore"])
        self.assertEqual(data["marriageCertificateSpouse1SurnameBefore"], "Иванов")

    def test_missing_patronymic_keeps_other_birth_fields(self) -> None:
        page = birth_page()
        page[3]["text"] = ""
        data = merge_birth_certificate_pages([page])
        self.assertIsNone(data["birthCertificateChildPatronymic"])
        self.assertEqual(data["birthCertificateChildGivenName"], "Алексей")
        self.assertEqual(data["birthCertificateFatherSurname"], "Петров")

    def test_ambiguous_spouse_sections_remain_empty(self) -> None:
        page = marriage_page()
        page.insert(5, {"text": "Он", "box": (0, 135, 400, 150)})
        data = merge_marriage_certificate_pages([page])
        self.assertIsNone(data["marriageCertificateSpouse1SurnameBefore"])
        self.assertEqual(data["marriageCertificateSpouse2SurnameBefore"], "Смирнова")


if __name__ == "__main__":
    unittest.main()
