import { execFile } from 'node:child_process';
import { join } from 'node:path';
import { promisify } from 'node:util';

import type { PassportData } from '../models/api.model';

const OCR_RESULT_PREFIX = 'OCR_RESULT:';
const OCR_TIMEOUT_MS = 10 * 60 * 1000;
const PASSPORT_DATA_FIELDS: readonly (keyof PassportData)[] = [
  'currentNationality',
  'dateOfBirth',
  'givenName',
  'issuedByCountry',
  'numberOfTravelDocument',
  'placeOfBirth',
  'sex',
  'surname',
  'validUntil',
];
const execFileAsync = promisify(execFile);

/** Runs local passport OCR and returns its validated structured result. */
export async function recognizePassport(appPath: string, imagePath: string): Promise<PassportData> {
  const pythonExecutable = join(appPath, '.venv-ocr', 'Scripts', 'python.exe');
  const scriptPath = join(appPath, 'ocr', 'recognize_passport.py');
  const { stdout } = await execFileAsync(pythonExecutable, [scriptPath, imagePath], {
    encoding: 'utf8',
    env: {
      ...process.env,
      PYTHONIOENCODING: 'utf-8',
    },
    timeout: OCR_TIMEOUT_MS,
    windowsHide: true,
  });

  console.log('Python stdout:', stdout);
  const resultLine = stdout.split(/\r?\n/).find((line) => line.startsWith(OCR_RESULT_PREFIX));

  if (!resultLine) {
    throw new Error('The OCR process returned no structured result.');
  }

  const passportData: unknown = JSON.parse(resultLine.slice(OCR_RESULT_PREFIX.length));

  if (!isPassportData(passportData)) {
    throw new Error('The OCR process returned an invalid result.');
  }

  return passportData;
}

function isPassportData(value: unknown): value is PassportData {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const passportData = value as Record<keyof PassportData, unknown>;
  return PASSPORT_DATA_FIELDS.every((field) => {
    const fieldValue = passportData[field];
    return fieldValue === null || typeof fieldValue === 'string';
  });
}
