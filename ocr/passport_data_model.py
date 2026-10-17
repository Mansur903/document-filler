from typing import Literal, TypedDict


DocumentType = Literal["passport", "russianInternalPassport", "uaeResidencePermit"]


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
