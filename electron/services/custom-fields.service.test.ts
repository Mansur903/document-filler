import assert from 'node:assert/strict';
import { mkdir, mkdtemp, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import { AppSettingsStore } from './app-settings.service';
import {
  createCustomField,
  deleteCustomField,
  listCustomFields,
  validateCustomField,
  validateCustomFieldValues,
} from './custom-fields.service';

const existingFields = [{ label: 'Extra phone', name: 'extraPhone' }];

test('accepts a unique field and trims its label', () => {
  assert.deepEqual(validateCustomField({ label: '  Note  ', name: 'customNote_2' }, existingFields), {
    label: 'Note',
    name: 'customNote_2',
  });
});

test('rejects missing labels, invalid names, reserved names, and collisions', () => {
  const invalidFields = [
    { label: '   ', name: 'note' },
    { label: 'Note', name: '2note' },
    { label: 'Note', name: 'my note' },
    { label: 'Note', name: '{note}' },
    { label: 'Note', name: 'constructor' },
    { label: 'Note', name: 'prototype' },
    { label: 'Note', name: '__proto__' },
    { label: 'Note', name: 'toString' },
    { label: 'Note', name: 'SURNAME' },
    { label: 'Note', name: 'EXTRAPHONE' },
  ];

  for (const field of invalidFields) {
    assert.throws(() => validateCustomField(field, existingFields));
  }
});

test('accepts only string values for saved custom fields', () => {
  assert.deepEqual(validateCustomFieldValues({ extraPhone: '123' }, existingFields), {
    extraPhone: '123',
  });
  assert.deepEqual(validateCustomFieldValues({}, existingFields), { extraPhone: '' });
  assert.throws(() => validateCustomFieldValues({ surname: 'Override' }, existingFields));
  assert.throws(() => validateCustomFieldValues({ extraPhone: 123 }, existingFields));
});

test('returns only definitions and persists creation and deletion', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'document-filler-fields-'));
  const settingsPath = join(directory, 'settings.json');

  try {
    const store = new AppSettingsStore(settingsPath);
    await store.update((settings) => ({ ...settings, lastDocumentDirectory: 'C:\\Documents' }));
    assert.deepEqual(await createCustomField(store, { label: 'Extra phone', name: 'extraPhone' }), [
      { label: 'Extra phone', name: 'extraPhone' },
    ]);
    assert.deepEqual(await listCustomFields(new AppSettingsStore(settingsPath)), [
      { label: 'Extra phone', name: 'extraPhone' },
    ]);
    assert.deepEqual(await deleteCustomField(store, 'extraPhone'), []);
    assert.deepEqual(await listCustomFields(new AppSettingsStore(settingsPath)), []);
    assert.equal((await store.read()).lastDocumentDirectory, 'C:\\Documents');
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('does not publish a definition if the settings file cannot be replaced', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'document-filler-fields-'));
  const settingsPath = join(directory, 'settings.json');

  try {
    const store = new AppSettingsStore(settingsPath);
    await store.read();
    await mkdir(settingsPath);
    await assert.rejects(
      createCustomField(store, { label: 'Extra phone', name: 'extraPhone' }),
      /could not be saved/,
    );
    assert.deepEqual(await listCustomFields(store), []);
    assert.deepEqual(await readdir(directory), ['settings.json']);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
