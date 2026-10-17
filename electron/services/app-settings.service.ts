import { randomUUID } from 'node:crypto';
import { mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { dirname } from 'node:path';

import type { CustomFieldDefinition } from '../models/ui.model';
import { validateCustomField } from './custom-fields.service';

export interface AppSettings {
  readonly version: 1;
  readonly lastDocumentDirectory: string | null;
  readonly lastTemplateDirectory: string | null;
  readonly customFields: readonly CustomFieldDefinition[];
}

const EMPTY_SETTINGS: AppSettings = {
  version: 1,
  lastDocumentDirectory: null,
  lastTemplateDirectory: null,
  customFields: [],
};

/** Stores application preferences outside the renderer process. */
export class AppSettingsStore {
  private settingsPromise: Promise<AppSettings> | null = null;
  private writeQueue: Promise<void> = Promise.resolve();

  constructor(private readonly filePath: string) {}

  /**
   * Returns a detached snapshot of the current settings.
   * @returns The validated settings snapshot.
   * @throws If the settings file cannot be read or parsed.
   */
  public async read(): Promise<AppSettings> {
    this.settingsPromise ??= this.readFromDisk();

    try {
      return cloneSettings(await this.settingsPromise);
    } catch (error) {
      this.settingsPromise = null;
      throw error;
    }
  }

  /**
   * Persists a settings change before publishing it to other callers.
   * @param change Computes the next settings from the current snapshot.
   * @returns The persisted settings snapshot.
   * @throws If the change is invalid or cannot be saved.
   */
  public async update(change: (settings: AppSettings) => AppSettings): Promise<AppSettings> {
    const operation = this.writeQueue.then(async () => {
      const next = change(await this.read());
      await this.writeToDisk(next);
      this.settingsPromise = Promise.resolve(cloneSettings(next));
      return cloneSettings(next);
    });

    this.writeQueue = operation.then(
      () => undefined,
      () => undefined,
    );

    return operation;
  }

  private async readFromDisk(): Promise<AppSettings> {
    let contents: string;

    try {
      contents = await readFile(this.filePath, 'utf8');
    } catch (error) {
      if (isMissingFile(error)) {
        return cloneSettings(EMPTY_SETTINGS);
      }

      throw new Error('Application settings could not be read.', { cause: error });
    }

    try {
      return parseSettings(JSON.parse(contents) as unknown);
    } catch (error) {
      throw new Error('Application settings are invalid.', { cause: error });
    }
  }

  private async writeToDisk(settings: AppSettings): Promise<void> {
    const temporaryPath = `${this.filePath}.${randomUUID()}.tmp`;

    try {
      await mkdir(dirname(this.filePath), { recursive: true });
      await writeFile(temporaryPath, JSON.stringify(settings, null, 2), 'utf8');
      await rename(temporaryPath, this.filePath);
    } catch (error) {
      await rm(temporaryPath, { force: true }).catch(() => undefined);
      throw new Error('Application settings could not be saved.', { cause: error });
    }
  }
}

function cloneSettings(settings: AppSettings): AppSettings {
  return {
    version: 1,
    lastDocumentDirectory: settings.lastDocumentDirectory,
    lastTemplateDirectory: settings.lastTemplateDirectory,
    customFields: settings.customFields.map((field) => ({ ...field })),
  };
}

function parseSettings(value: unknown): AppSettings {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('The settings document must be an object.');
  }

  const data = value as Record<string, unknown>;

  if (data['version'] !== 1) {
    throw new Error('Unsupported settings version.');
  }

  const fields = Array.isArray(data['customFields']) ? data['customFields'] : [];
  const customFields: CustomFieldDefinition[] = [];

  for (const field of fields) {
    try {
      customFields.push(validateCustomField(field, customFields));
    } catch {
      // Ignore a malformed stored field without discarding other preferences.
    }
  }

  return {
    version: 1,
    lastDocumentDirectory: stringOrNull(data['lastDocumentDirectory']),
    lastTemplateDirectory: stringOrNull(data['lastTemplateDirectory']),
    customFields,
  };
}

function stringOrNull(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

function isMissingFile(error: unknown): boolean {
  return typeof error === 'object' && error !== null && 'code' in error && error.code === 'ENOENT';
}
