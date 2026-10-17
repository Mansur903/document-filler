import type { CustomFieldDefinition } from '../models/ui.model';
import type { AppSettingsStore } from './app-settings.service';
import { PERSONAL_FORM_FIELDS } from './document-generation.service';

const FIELD_NAME_PATTERN = /^[A-Za-z][A-Za-z0-9_]*$/;
const RESERVED_NAMES = new Set([
  ...Object.getOwnPropertyNames(Object.prototype).map((name) => name.toLowerCase()),
  'prototype',
]);
const STANDARD_NAMES = new Set(PERSONAL_FORM_FIELDS.map((name) => name.toLowerCase()));

/** Returns only renderer-safe field definitions. */
export async function listCustomFields(
  settingsStore: AppSettingsStore,
): Promise<readonly CustomFieldDefinition[]> {
  return (await settingsStore.read()).customFields;
}

/** Creates a field after validation and successful persistence. */
export async function createCustomField(
  settingsStore: AppSettingsStore,
  definition: unknown,
): Promise<readonly CustomFieldDefinition[]> {
  return (
    await settingsStore.update((settings) => ({
      ...settings,
      customFields: [
        ...settings.customFields,
        validateCustomField(definition, settings.customFields),
      ],
    }))
  ).customFields;
}

/** Deletes an existing field after successful persistence. */
export async function deleteCustomField(
  settingsStore: AppSettingsStore,
  name: unknown,
): Promise<readonly CustomFieldDefinition[]> {
  if (typeof name !== 'string') {
    throw new Error('The custom field name is invalid.');
  }

  return (
    await settingsStore.update((settings) => {
      if (!settings.customFields.some((field) => field.name === name)) {
        throw new Error('The custom field does not exist.');
      }

      return {
        ...settings,
        customFields: settings.customFields.filter((field) => field.name !== name),
      };
    })
  ).customFields;
}

/** Validates and normalizes a new custom field definition. */
export function validateCustomField(
  value: unknown,
  existingFields: readonly CustomFieldDefinition[],
): CustomFieldDefinition {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Enter a label and placeholder name.');
  }

  const input = value as Record<string, unknown>;
  const label = typeof input['label'] === 'string' ? input['label'].trim() : '';
  const name = input['name'];

  if (!label) {
    throw new Error('Enter a field label.');
  }

  if (typeof name !== 'string' || !FIELD_NAME_PATTERN.test(name)) {
    throw new Error('Use a placeholder name starting with a letter and containing only letters, numbers, or underscores.');
  }

  const normalizedName = name.toLowerCase();

  if (
    RESERVED_NAMES.has(normalizedName) ||
    STANDARD_NAMES.has(normalizedName) ||
    existingFields.some((field) => field.name.toLowerCase() === normalizedName)
  ) {
    throw new Error('This placeholder name is already used or reserved.');
  }

  return { label, name };
}

/** Validates the dynamic values sent to the DOCX generator. */
export function validateCustomFieldValues(
  value: unknown,
  definitions: readonly CustomFieldDefinition[],
): Record<string, string> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Custom field values are invalid.');
  }

  const input = value as Record<string, unknown>;
  const allowedNames = new Set(definitions.map((field) => field.name));

  for (const [name, fieldValue] of Object.entries(input)) {
    if (!allowedNames.has(name) || typeof fieldValue !== 'string') {
      throw new Error('Custom field values are invalid.');
    }
  }

  return Object.fromEntries(definitions.map(({ name }) => [name, input[name] ?? ''])) as Record<
    string,
    string
  >;
}
