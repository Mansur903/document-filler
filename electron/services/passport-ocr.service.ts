import { app } from 'electron';
import { execFile } from 'node:child_process';
import { join } from 'node:path';
import { promisify } from 'node:util';

import type {
  InternalPassportData,
  PassportData,
  RecognizedDocumentData,
  ResidencePermitData,
} from '../models/api.model';
import type { DocumentType } from '../models/ui.model';

const OCR_RESULT_PREFIX = 'OCR_RESULT:';
const OCR_TIMEOUT_MS = 10 * 60 * 1000;
const PASSPORT_DATA_FIELDS: readonly (keyof PassportData)[] = [
  'authority',
  'currentNationality',
  'dateOfBirth',
  'dateOfIssue',
  'givenName',
  'issuedByCountry',
  'numberOfTravelDocument',
  'placeOfBirth',
  'sex',
  'surname',
  'validUntil',
];
const INTERNAL_PASSPORT_DATA_FIELDS: readonly (keyof InternalPassportData)[] = [
  'authority',
  'dateOfBirth',
  'dateOfIssue',
  'givenName',
  'internalPassportNumber',
  'internalPassportSeries',
  'patronymic',
  'placeOfBirth',
  'sex',
  'subdivisionCode',
  'surname',
];
const RESIDENCE_PERMIT_DATA_FIELDS: readonly (keyof ResidencePermitData)[] = [
  'currentOccupation',
  'employer',
  'residencepermitID',
  'visaID',
  'visaValidUntil',
];
const execFileAsync = promisify(execFile);

/**
 * Runs local OCR with the parser selected for the document type.
 * @param documentPath Absolute path retained by Electron main.
 * @param documentType Parser to use for the selected document.
 * @returns Validated structured OCR data.
 * @throws If the OCR worker fails or returns an invalid payload.
 */
export async function recognizeDocument(
  documentPath: string,
  documentType: DocumentType,
): Promise<RecognizedDocumentData> {
  const executable = app.isPackaged
    ? join(process.resourcesPath, 'ocr', 'ocr.exe')
    : join(app.getAppPath(), '.venv-ocr', 'Scripts', 'python.exe');
  const argumentsList = app.isPackaged
    ? [documentType, documentPath]
    : [join(app.getAppPath(), 'ocr', 'recognize_passport.py'), documentType, documentPath];
  const { stdout } = await execFileAsync(executable, argumentsList, {
    encoding: 'utf8',
    env: {
      ...process.env,
      PYTHONIOENCODING: 'utf-8',
    },
    timeout: OCR_TIMEOUT_MS,
    windowsHide: true,
  });

  const resultLine = stdout.split(/\r?\n/).find((line) => line.startsWith(OCR_RESULT_PREFIX));

  if (!resultLine) {
    throw new Error('The OCR process returned no structured result.');
  }

  const documentData: unknown = JSON.parse(resultLine.slice(OCR_RESULT_PREFIX.length));

  if (!isRecognizedDocumentData(documentData, documentType)) {
    throw new Error('The OCR process returned an invalid result.');
  }

  return documentData;
}

/**
 * Checks that an OCR payload has exactly the fields for the selected document type.
 * @param value Parsed OCR payload.
 * @param documentType Selected document type.
 * @returns Whether the payload matches the selected document contract.
 */
export function isRecognizedDocumentData(
  value: unknown,
  documentType: DocumentType,
): value is RecognizedDocumentData {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const fields = documentType === 'passport'
    ? PASSPORT_DATA_FIELDS
    : documentType === 'russianInternalPassport'
      ? INTERNAL_PASSPORT_DATA_FIELDS
      : RESIDENCE_PERMIT_DATA_FIELDS;
  const data = value as Record<string, unknown>;

  return Object.keys(data).length === fields.length && fields.every((field) => {
    const fieldValue = data[field];
    return fieldValue === null || typeof fieldValue === 'string';
  });
}
