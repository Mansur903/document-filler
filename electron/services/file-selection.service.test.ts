import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import { AppSettingsStore } from './app-settings.service';
import {
  getDialogDefaultPath,
  selectRememberedFile,
  validateReadableTemplatePath,
} from './file-selection.service';

test('remembers independent document and template folders across store instances', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'document-filler-dialogs-'));
  const documentDirectory = await mkdtemp(join(directory, 'documents-'));
  const templateDirectory = await mkdtemp(join(directory, 'templates-'));
  const settingsPath = join(directory, 'settings.json');
  const store = new AppSettingsStore(settingsPath);
  const defaults: Array<string | undefined> = [];

  try {
    await selectRememberedFile(
      store,
      'lastDocumentDirectory',
      async (defaultPath) => {
        defaults.push(defaultPath);
        return { canceled: false, filePaths: [join(documentDirectory, 'passport.pdf')] };
      },
      async (filePath) => filePath,
    );
    await selectRememberedFile(
      store,
      'lastTemplateDirectory',
      async (defaultPath) => {
        defaults.push(defaultPath);
        return { canceled: false, filePaths: [join(templateDirectory, 'template.docx')] };
      },
      async (filePath) => filePath,
    );

    const restartedStore = new AppSettingsStore(settingsPath);
    assert.equal(await getDialogDefaultPath(restartedStore, 'lastDocumentDirectory'), documentDirectory);
    assert.equal(await getDialogDefaultPath(restartedStore, 'lastTemplateDirectory'), templateDirectory);
    assert.deepEqual(defaults, [undefined, undefined]);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('cancellation and file rejection leave the remembered folder unchanged', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'document-filler-dialogs-'));
  const settingsPath = join(directory, 'settings.json');
  const store = new AppSettingsStore(settingsPath);

  try {
    await store.update((settings) => ({ ...settings, lastTemplateDirectory: directory }));
    assert.equal(
      await selectRememberedFile(
        store,
        'lastTemplateDirectory',
        async () => ({ canceled: true, filePaths: [] }),
        async () => 'unreachable',
      ),
      null,
    );
    await assert.rejects(
      selectRememberedFile(
        store,
        'lastTemplateDirectory',
        async () => ({ canceled: false, filePaths: [join(directory, 'invalid.pdf')] }),
        async () => {
          throw new Error('Unsupported template');
        },
      ),
      /Unsupported template/,
    );
    assert.equal((await store.read()).lastTemplateDirectory, directory);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('ignores a missing saved folder', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'document-filler-dialogs-'));
  const store = new AppSettingsStore(join(directory, 'settings.json'));

  try {
    await store.update((settings) => ({
      ...settings,
      lastDocumentDirectory: join(directory, 'missing'),
    }));
    assert.equal(await getDialogDefaultPath(store, 'lastDocumentDirectory'), undefined);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('accepts readable DOCX templates and rejects unsupported or missing files', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'document-filler-dialogs-'));
  const templatePath = join(directory, 'template.docx');

  try {
    await writeFile(templatePath, 'example');
    await validateReadableTemplatePath(templatePath);
    await assert.rejects(validateReadableTemplatePath(join(directory, 'template.pdf')), /DOCX/);
    await assert.rejects(validateReadableTemplatePath(join(directory, 'missing.docx')));
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
