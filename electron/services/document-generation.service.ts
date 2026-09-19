import Docxtemplater from 'docxtemplater';
import { readFile } from 'node:fs/promises';
import PizZip from 'pizzip';

import type { PassportFormData } from '../models/api.model';

const PASSPORT_FORM_FIELDS: readonly (keyof PassportFormData)[] = [
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

/**
 * Fills a DOCX template with passport form values.
 * @param templatePath Path to the selected DOCX template.
 * @param data Current editable passport form values.
 * @returns Generated DOCX contents.
 * @throws If the template cannot be read or rendered.
 */
export async function generateDocument(
  templatePath: string,
  data: PassportFormData,
): Promise<Buffer> {
  const template = await readFile(templatePath);
  const document = new Docxtemplater(new PizZip(template), {
    linebreaks: true,
    nullGetter: (part) => `{${part.value}}`,
    paragraphLoop: true,
  });

  document.render({
    ...data,
    dateOfBirth: formatDate(data.dateOfBirth),
    dateOfIssue: formatDate(data.dateOfIssue),
    validUntil: formatDate(data.validUntil),
  });

  return document.getZip().generate({ compression: 'DEFLATE', type: 'nodebuffer' });
}

/**
 * Checks an IPC payload before it is used as template data.
 * @param value Value received from the renderer.
 * @returns Whether the value contains all expected string fields.
 */
export function isPassportFormData(value: unknown): value is PassportFormData {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const data = value as Record<keyof PassportFormData, unknown>;
  return PASSPORT_FORM_FIELDS.every((field) => typeof data[field] === 'string');
}

function formatDate(value: string): string {
  const [year, month, day] = value.split('-');
  return year && month && day ? `${day}.${month}.${year}` : value;
}
