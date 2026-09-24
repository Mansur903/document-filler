import Docxtemplater from 'docxtemplater';
import { readFile } from 'node:fs/promises';
import PizZip from 'pizzip';

import type { PersonalFormData } from '../models/api.model';

const PERSONAL_FORM_FIELDS: readonly (keyof PersonalFormData)[] = [
  'address',
  'currentNationality',
  'currentOccupation',
  'dateOfBirth',
  'dateOfIssue',
  'email',
  'employer',
  'givenName',
  'issuedByCountry',
  'numberOfTravelDocument',
  'phone',
  'placeOfBirth',
  'residencepermitID',
  'sex',
  'surname',
  'validUntil',
  'visaID',
  'visaValidUntil',
];

/**
 * Fills a DOCX template with passport form values.
 * @param templatePath Path to the selected DOCX template.
 * @param data Current editable personal form values.
 * @returns Generated DOCX contents.
 * @throws If the template cannot be read or rendered.
 */
export async function generateDocument(
  templatePath: string,
  data: PersonalFormData,
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
    visaValidUntil: formatDate(data.visaValidUntil),
  });

  return document.getZip().generate({ compression: 'DEFLATE', type: 'nodebuffer' });
}

/**
 * Checks an IPC payload before it is used as template data.
 * @param value Value received from the renderer.
 * @returns Whether the value contains all expected string fields.
 */
export function isPersonalFormData(value: unknown): value is PersonalFormData {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const data = value as Record<keyof PersonalFormData, unknown>;
  return PERSONAL_FORM_FIELDS.every((field) => typeof data[field] === 'string');
}

function formatDate(value: string): string {
  const [year, month, day] = value.split('-');
  return year && month && day ? `${day}.${month}.${year}` : value;
}
