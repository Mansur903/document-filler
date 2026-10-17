import assert from 'node:assert/strict';
import { mkdir, mkdtemp, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import { AppSettingsStore } from './app-settings.service';

test('starts empty, persists separate preferences, and reloads them', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'document-filler-settings-'));
  const filePath = join(directory, 'settings.json');

  try {
    const store = new AppSettingsStore(filePath);
    assert.deepEqual(await store.read(), {
      version: 1,
      lastDocumentDirectory: null,
      lastTemplateDirectory: null,
      customFields: [],
    });

    await store.update((settings) => ({
      ...settings,
      lastDocumentDirectory: 'C:\\Documents',
      lastTemplateDirectory: 'C:\\Templates',
      customFields: [{ label: 'Extra phone', name: 'extraPhone' }],
    }));

    assert.deepEqual(await new AppSettingsStore(filePath).read(), {
      version: 1,
      lastDocumentDirectory: 'C:\\Documents',
      lastTemplateDirectory: 'C:\\Templates',
      customFields: [{ label: 'Extra phone', name: 'extraPhone' }],
    });
    assert.deepEqual(await readdir(directory), ['settings.json']);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('ignores malformed stored entries and preserves valid preferences', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'document-filler-settings-'));
  const filePath = join(directory, 'settings.json');

  try {
    await writeFile(
      filePath,
      JSON.stringify({
        version: 1,
        lastDocumentDirectory: 'C:\\Documents',
        lastTemplateDirectory: 42,
        customFields: [
          { label: 'Extra phone', name: 'extraPhone' },
          { label: '', name: 'emptyLabel' },
          { label: 'Duplicate', name: 'EXTRAPHONE' },
          { label: 'Built in', name: 'surname' },
          { label: 'Other', name: 'otherField' },
        ],
      }),
    );

    assert.deepEqual(await new AppSettingsStore(filePath).read(), {
      version: 1,
      lastDocumentDirectory: 'C:\\Documents',
      lastTemplateDirectory: null,
      customFields: [
        { label: 'Extra phone', name: 'extraPhone' },
        { label: 'Other', name: 'otherField' },
      ],
    });
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('leaves the previous settings intact when a change fails', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'document-filler-settings-'));
  const filePath = join(directory, 'settings.json');

  try {
    const store = new AppSettingsStore(filePath);
    await store.update((settings) => ({ ...settings, lastDocumentDirectory: 'C:\\Documents' }));
    const before = await readFile(filePath, 'utf8');

    await assert.rejects(
      store.update(() => {
        throw new Error('Rejected change');
      }),
      /Rejected change/,
    );

    assert.equal(await readFile(filePath, 'utf8'), before);
    assert.equal((await store.read()).lastDocumentDirectory, 'C:\\Documents');
    assert.deepEqual(await readdir(directory), ['settings.json']);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('removes a temporary file and keeps the cached state when replacement fails', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'document-filler-settings-'));
  const filePath = join(directory, 'settings.json');

  try {
    const store = new AppSettingsStore(filePath);
    await store.read();
    await mkdir(filePath);

    await assert.rejects(
      store.update((settings) => ({ ...settings, lastDocumentDirectory: 'C:\\Documents' })),
      /could not be saved/,
    );

    assert.deepEqual(await readdir(directory), ['settings.json']);
    assert.equal((await store.read()).lastDocumentDirectory, null);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
