from typing import Literal, TypedDict


DocumentType = Literal[
    "passport",
    "russianBirthCertificate",
    "russianInternalPassport",
    "russianMarriageCertificate",
    "uaeResidencePermit",
]


class OcrTextBlock(TypedDict):
    box: tuple[int, int, int, int]
    text: str


class PassportData(TypedDict):
    authority: str | None
    currentNationality: str | None
    dateOfBirth: str | None
    dateOfIssue: str | None
    givenName: str | None
    issuedByCountry: str | None
    numberOfTravelDocument: str | None
    placeOfBirth: str | None
    sex: str | None
    surname: str | None
    validUntil: str | None


class InternalPassportData(TypedDict):
    authority: str | None
    dateOfBirth: str | None
    dateOfIssue: str | None
    givenName: str | None
    internalPassportNumber: str | None
    internalPassportSeries: str | None
    patronymic: str | None
    placeOfBirth: str | None
    sex: str | None
    subdivisionCode: str | None
    surname: str | None


class ResidencePermitData(TypedDict):
    currentOccupation: str | None
    employer: str | None
    residencepermitID: str | None
    visaID: str | None
    visaValidUntil: str | None


class BirthCertificateData(TypedDict):
    birthCertificateChildSurname: str | None
    birthCertificateChildGivenName: str | None
    birthCertificateChildPatronymic: str | None
    birthCertificateChildDateOfBirth: str | None
    birthCertificateChildPlaceOfBirth: str | None
    birthCertificateFatherSurname: str | None
    birthCertificateFatherGivenName: str | None
    birthCertificateFatherPatronymic: str | None
    birthCertificateFatherDateOfBirth: str | None
    birthCertificateFatherCitizenship: str | None
    birthCertificateFatherNationality: str | None
    birthCertificateMotherSurname: str | None
    birthCertificateMotherGivenName: str | None
    birthCertificateMotherPatronymic: str | None
    birthCertificateMotherDateOfBirth: str | None
    birthCertificateMotherCitizenship: str | None
    birthCertificateMotherNationality: str | None
    birthCertificateRegistrationDate: str | None
    birthCertificateRecordNumber: str | None
    birthCertificateRegistryOffice: str | None
    birthCertificateIssueDate: str | None
    birthCertificateSeries: str | None
    birthCertificateNumber: str | None


class MarriageCertificateData(TypedDict):
    marriageCertificateSpouse1SurnameBefore: str | None
    marriageCertificateSpouse1GivenNameBefore: str | None
    marriageCertificateSpouse1PatronymicBefore: str | None
    marriageCertificateSpouse1DateOfBirth: str | None
    marriageCertificateSpouse1PlaceOfBirth: str | None
    marriageCertificateSpouse1Citizenship: str | None
    marriageCertificateSpouse1Nationality: str | None
    marriageCertificateSpouse1SurnameAfter: str | None
    marriageCertificateSpouse2SurnameBefore: str | None
    marriageCertificateSpouse2GivenNameBefore: str | None
    marriageCertificateSpouse2PatronymicBefore: str | None
    marriageCertificateSpouse2DateOfBirth: str | None
    marriageCertificateSpouse2PlaceOfBirth: str | None
    marriageCertificateSpouse2Citizenship: str | None
    marriageCertificateSpouse2Nationality: str | None
    marriageCertificateSpouse2SurnameAfter: str | None
    marriageCertificateMarriageDate: str | None
    marriageCertificateRecordDate: str | None
    marriageCertificateRecordNumber: str | None
    marriageCertificateRegistryOffice: str | None
    marriageCertificateIssueDate: str | None
    marriageCertificateSeries: str | None
    marriageCertificateNumber: str | None
