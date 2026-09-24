import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import PizZip from 'pizzip';

import type { PersonalFormData } from '../models/api.model';
import { generateDocument, isPersonalFormData } from './document-generation.service';

const personalData: PersonalFormData = {
  address: 'Example address',
  currentNationality: 'RUS',
  currentOccupation: 'Engineer',
  dateOfBirth: '1990-01-01',
  dateOfIssue: '2020-01-02',
  email: '',
  employer: 'Example Company',
  givenName: 'Ivan',
  issuedByCountry: 'RUS',
  numberOfTravelDocument: '123456789',
  phone: '',
  placeOfBirth: 'Moscow',
  residencepermitID: '784200910498284',
  sex: 'M',
  surname: 'Ivanov',
  validUntil: '2030-01-03',
  visaID: '201/2024/3821949',
  visaValidUntil: '2027-08-28',
};

test('generates all personal placeholders and formats both validity dates', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'document-filler-'));
  const templatePath = join(directory, 'template.docx');

  try {
    await writeFile(templatePath, createTemplate());
    const output = await generateDocument(templatePath, personalData);
    const documentXml = new PizZip(output).file('word/document.xml')?.asText();

    assert.ok(documentXml);
    assert.match(documentXml, /Ivanov/);
    assert.match(documentXml, /784200910498284/);
    assert.match(documentXml, /201\/2024\/3821949/);
    assert.match(documentXml, /03\.01\.2030/);
    assert.match(documentXml, /28\.08\.2027/);
    assert.doesNotMatch(documentXml, /\{email\}|\{phone\}/);
  } finally {
    await rm(directory, { force: true, recursive: true });
  }
});

test('validates the complete personal form payload', () => {
  assert.equal(isPersonalFormData(personalData), true);
  assert.equal(isPersonalFormData({ ...personalData, visaValidUntil: null }), false);
  assert.equal(isPersonalFormData({ surname: 'Ivanov' }), false);
});

function createTemplate(): Buffer {
  const archive = new PizZip();
  archive.file(
    '[Content_Types].xml',
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
      '<Default Extension="xml" ContentType="application/xml"/>' +
      '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>' +
      '</Types>',
  );
  archive.file(
    '_rels/.rels',
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>' +
      '</Relationships>',
  );
  archive.file(
    'word/document.xml',
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' +
      '<w:body><w:p><w:r><w:t>' +
      '{surname}|{residencepermitID}|{visaID}|{validUntil}|{visaValidUntil}|{email}|{phone}' +
      '</w:t></w:r></w:p></w:body></w:document>',
  );
  archive.file(
    'word/_rels/document.xml.rels',
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
  );
  return archive.generate({ type: 'nodebuffer' });
}
