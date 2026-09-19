from typing import TypedDict


class OcrTextBlock(TypedDict):
    box: tuple[int, int, int, int]
    text: str


class PassportData(TypedDict):
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
