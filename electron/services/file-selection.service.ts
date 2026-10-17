import { constants } from 'node:fs';
import { access, stat } from 'node:fs/promises';
import { dirname, extname } from 'node:path';

import type { AppSettings } from './app-settings.service';
import { AppSettingsStore } from './app-settings.service';

export type DirectoryPreferenceKey =
  | 'lastDocumentDirectory'
  | 'lastTemplateDirectory';

export interface FileDialogResult {
  readonly canceled: boolean;
  readonly filePaths: readonly string[];
}

/** Returns an available saved folder for a native file dialog. */
export async function getDialogDefaultPath(
  settingsStore: AppSettingsStore,
  key: DirectoryPreferenceKey,
): Promise<string | undefined> {
  const directory = (await settingsStore.read())[key];

  if (!directory) {
    return undefined;
  }

  try {
    if (!(await stat(directory)).isDirectory()) {
      return undefined;
    }

    await access(directory, constants.R_OK);
    return directory;
  } catch {
    return undefined;
  }
}

/** Accepts a file and persists its parent folder for the next dialog. */
export async function selectRememberedFile<T>(
  settingsStore: AppSettingsStore,
  key: DirectoryPreferenceKey,
  openDialog: (defaultPath: string | undefined) => Promise<FileDialogResult>,
  acceptFile: (filePath: string) => Promise<T>,
): Promise<T | null> {
  const result = await openDialog(await getDialogDefaultPath(settingsStore, key));

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }

  const filePath = result.filePaths[0];
  const accepted = await acceptFile(filePath);
  const directory = dirname(filePath);

  await settingsStore.update((settings): AppSettings => ({
    ...settings,
    [key]: directory,
  }));

  return accepted;
}

/** Rejects unreadable files and formats other than DOCX. */
export async function validateReadableTemplatePath(filePath: string): Promise<void> {
  if (extname(filePath).toLowerCase() !== '.docx') {
    throw new Error('Only DOCX templates are supported.');
  }

  await access(filePath, constants.R_OK);
}
