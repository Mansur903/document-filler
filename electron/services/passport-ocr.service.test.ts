import assert from 'node:assert/strict';
import test from 'node:test';

import type { InternalPassportData } from '../models/api.model';
import {
  BIRTH_CERTIFICATE_DATA_FIELDS,
  MARRIAGE_CERTIFICATE_DATA_FIELDS,
} from '../models/certificate-fields';
import { isRecognizedDocumentData } from './passport-ocr.service';

const internalPassportData: InternalPassportData = {
  authority: 'Example authority',
  dateOfBirth: '1992-04-03',
  dateOfIssue: '2019-02-11',
  givenName: 'ANNA',
  internalPassportNumber: '567890',
  internalPassportSeries: '1234',
  patronymic: null,
  placeOfBirth: 'Example city',
  sex: 'F',
  subdivisionCode: '123-456',
  surname: 'IVANOVA',
};

test('accepts the complete internal passport contract', () => {
  assert.equal(isRecognizedDocumentData(internalPassportData, 'russianInternalPassport'), true);
  assert.equal(isRecognizedDocumentData(internalPassportData, 'passport'), false);
});

test('rejects incomplete, wrong-type, and extra OCR fields', () => {
  const incomplete = { ...internalPassportData } as Record<string, unknown>;
  delete incomplete['subdivisionCode'];

  assert.equal(isRecognizedDocumentData(incomplete, 'russianInternalPassport'), false);
  assert.equal(
    isRecognizedDocumentData({ ...internalPassportData, sex: 1 }, 'russianInternalPassport'),
    false,
  );
  assert.equal(
    isRecognizedDocumentData(
      { ...internalPassportData, numberOfTravelDocument: '123456789' },
      'russianInternalPassport',
    ),
    false,
  );
});

test('retains the existing passport and permit result contracts', () => {
  const passportFields = [
    'authority', 'currentNationality', 'dateOfBirth', 'dateOfIssue', 'givenName',
    'issuedByCountry', 'numberOfTravelDocument', 'placeOfBirth', 'sex', 'surname', 'validUntil',
  ];
  const permitFields = [
    'currentOccupation', 'employer', 'residencepermitID', 'visaID', 'visaValidUntil',
  ];
  assert.equal(
    isRecognizedDocumentData(Object.fromEntries(passportFields.map((field) => [field, null])), 'passport'),
    true,
  );
  assert.equal(
    isRecognizedDocumentData(Object.fromEntries(permitFields.map((field) => [field, null])), 'uaeResidencePermit'),
    true,
  );
});

test('accepts exact civil certificate contracts and rejects extra fields', () => {
  const birth = Object.fromEntries(BIRTH_CERTIFICATE_DATA_FIELDS.map((field) => [field, null]));
  const marriage = Object.fromEntries(MARRIAGE_CERTIFICATE_DATA_FIELDS.map((field) => [field, null]));

  assert.equal(isRecognizedDocumentData(birth, 'russianBirthCertificate'), true);
  assert.equal(isRecognizedDocumentData(marriage, 'russianMarriageCertificate'), true);
  assert.equal(isRecognizedDocumentData(birth, 'russianMarriageCertificate'), false);
  assert.equal(isRecognizedDocumentData(marriage, 'russianBirthCertificate'), false);
  assert.equal(isRecognizedDocumentData({ ...birth, unexpected: 'value' }, 'russianBirthCertificate'), false);
  assert.equal(isRecognizedDocumentData({ ...marriage, marriageCertificateRecordDate: 42 }, 'russianMarriageCertificate'), false);
});
