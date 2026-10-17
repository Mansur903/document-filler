import { ChangeDetectionStrategy, Component, ElementRef, signal, viewChild } from '@angular/core';
import type { OnInit } from '@angular/core';
import { FormControl, FormGroup, FormRecord, ReactiveFormsModule } from '@angular/forms';

import type { PassportData, RecognizedDocumentData, ResidencePermitData } from './models/api.model';
import type {
  CustomFieldDefinition,
  DocumentType,
  GeneratedDocument,
  SelectedDocumentFile,
  SelectedTemplate,
} from './models/ui.model';

type RecognizedField = keyof PassportData | keyof ResidencePermitData;

const DATE_FIELDS: ReadonlySet<RecognizedField> = new Set([
  'dateOfBirth',
  'dateOfIssue',
  'validUntil',
  'visaValidUntil',
]);
const ISO_DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;
const CUSTOM_FIELD_NAME_PATTERN = /^[A-Za-z][A-Za-z0-9_]*$/;
const RESERVED_CUSTOM_FIELD_NAMES = new Set([
  ...Object.getOwnPropertyNames(Object.prototype).map((name) => name.toLowerCase()),
  'prototype',
]);

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule],
  selector: 'tmt-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App implements OnInit {
  protected readonly addFieldButton = viewChild<ElementRef<HTMLButtonElement>>('addFieldButton');
  protected readonly createFieldDialog = viewChild<ElementRef<HTMLDialogElement>>('createFieldDialog');

  protected readonly createFieldForm = new FormGroup({
    label: new FormControl('', { nonNullable: true }),
    name: new FormControl('', { nonNullable: true }),
  });
  protected readonly customFieldControls = new FormRecord<FormControl<string>>({});
  protected readonly customFieldError = signal<string | null>(null);
  protected readonly customFields = signal<readonly CustomFieldDefinition[]>([]);
  protected readonly documentType = signal<DocumentType>('passport');
  protected readonly generatedDocument = signal<GeneratedDocument | null>(null);
  protected readonly generationError = signal<string | null>(null);
  protected readonly isConfirmingReset = signal(false);
  protected readonly isGenerating = signal(false);
  protected readonly isLoadingCustomFields = signal(true);
  protected readonly isSavingCustomField = signal(false);
  protected readonly isRecognizing = signal(false);
  protected readonly isSelecting = signal(false);
  protected readonly isSelectingTemplate = signal(false);
  protected readonly personalForm = new FormGroup({
    address: new FormControl('', { nonNullable: true }),
    authority: new FormControl('', { nonNullable: true }),
    currentNationality: new FormControl('', { nonNullable: true }),
    currentOccupation: new FormControl('', { nonNullable: true }),
    dateOfBirth: new FormControl('', { nonNullable: true }),
    dateOfIssue: new FormControl('', { nonNullable: true }),
    email: new FormControl('', { nonNullable: true }),
    employer: new FormControl('', { nonNullable: true }),
    givenName: new FormControl('', { nonNullable: true }),
    issuedByCountry: new FormControl('', { nonNullable: true }),
    numberOfTravelDocument: new FormControl('', { nonNullable: true }),
    phone: new FormControl('', { nonNullable: true }),
    placeOfBirth: new FormControl('', { nonNullable: true }),
    residencepermitID: new FormControl('', { nonNullable: true }),
    sex: new FormControl('', { nonNullable: true }),
    surname: new FormControl('', { nonNullable: true }),
    validUntil: new FormControl('', { nonNullable: true }),
    visaID: new FormControl('', { nonNullable: true }),
    visaValidUntil: new FormControl('', { nonNullable: true }),
  });
  protected readonly recognitionError = signal<string | null>(null);
  protected readonly selectedDocumentFile = signal<SelectedDocumentFile | null>(null);
  protected readonly selectedTemplate = signal<SelectedTemplate | null>(null);
  protected readonly selectionError = signal<string | null>(null);
  protected readonly templateSelectionError = signal<string | null>(null);

  protected get documentTypeLabel(): string {
    return this.documentType() === 'passport' ? 'Russian passport' : 'UAE Residence Permit';
  }

  /** Loads saved field definitions with empty session values. */
  public ngOnInit(): void {
    void this.loadCustomFields();
  }

  /** Opens the custom field creation dialog. */
  protected onOpenCreateCustomField(): void {
    if (this.isLoadingCustomFields()) {
      return;
    }

    this.createFieldForm.reset();
    this.customFieldError.set(null);
    const dialog = this.createFieldDialog()?.nativeElement;

    if (!dialog) {
      return;
    }

    if (typeof dialog.showModal === 'function') {
      dialog.showModal();
    } else {
      dialog.setAttribute('open', '');
    }

    queueMicrotask(() => dialog.querySelector<HTMLInputElement>('input')?.focus());
  }

  /** Closes the creation dialog without changing field definitions. */
  protected onCancelCreateCustomField(): void {
    this.closeCreateFieldDialog();
    this.createFieldForm.reset();
    this.customFieldError.set(null);
  }

  /** Saves a validated field definition. */
  protected async onSaveCustomField(): Promise<void> {
    const definition = this.createFieldForm.getRawValue();
    const error = this.getCustomFieldValidationError(definition);

    if (error) {
      this.customFieldError.set(error);
      return;
    }

    if (!window.electronAPI) {
      this.customFieldError.set('Custom fields are available only in the desktop application.');
      return;
    }

    this.isSavingCustomField.set(true);
    this.customFieldError.set(null);

    try {
      const fields = await window.electronAPI.createCustomField(definition);
      this.syncCustomFields(fields);
      this.closeCreateFieldDialog();
    } catch {
      this.customFieldError.set('The custom field could not be saved. Please try again.');
    } finally {
      this.isSavingCustomField.set(false);
    }
  }

  /** Removes a saved field and its current value. */
  protected async onDeleteCustomField(name: string): Promise<void> {
    if (!window.electronAPI) {
      return;
    }

    this.customFieldError.set(null);

    try {
      this.syncCustomFields(await window.electronAPI.deleteCustomField(name));
    } catch {
      this.customFieldError.set('The custom field could not be deleted. Please try again.');
    }
  }

  /** Selects the parser used for the next recognition. */
  protected onDocumentTypeChange(documentType: DocumentType): void {
    this.documentType.set(documentType);
    this.recognitionError.set(null);
  }

  /** Opens the native document picker and stores safe file metadata. */
  protected async onSelectDocumentFile(): Promise<void> {
    if (!window.electronAPI) {
      this.selectionError.set('Document selection is available only in the desktop application.');
      return;
    }

    this.isSelecting.set(true);
    this.selectionError.set(null);

    try {
      const documentFile = await window.electronAPI.selectDocumentFile();

      if (documentFile) {
        this.generatedDocument.set(null);
        this.generationError.set(null);
        this.recognitionError.set(null);
        this.selectedDocumentFile.set(documentFile);
      }
    } catch {
      this.selectionError.set(
        'The document could not be opened. Please try another JPG, JPEG, PNG, or PDF file.',
      );
    } finally {
      this.isSelecting.set(false);
    }
  }

  /** Recognizes the selected document and fills only empty form fields. */
  protected async onRecognizeDocument(): Promise<void> {
    if (!this.selectedDocumentFile() || this.isRecognizing()) {
      return;
    }

    this.isRecognizing.set(true);
    this.recognitionError.set(null);

    try {
      const documentData = await window.electronAPI.recognizeDocument(this.documentType());
      this.mergeRecognizedData(documentData);
      this.generatedDocument.set(null);
      this.generationError.set(null);
    } catch {
      this.recognitionError.set(
        `${this.documentTypeLabel} could not be recognized. Check the file and OCR setup.`,
      );
    } finally {
      this.isRecognizing.set(false);
    }
  }

  /** Opens the native picker and stores the selected DOCX template name. */
  protected async onSelectTemplate(): Promise<void> {
    if (!window.electronAPI) {
      this.templateSelectionError.set(
        'Template selection is available only in the desktop application.',
      );
      return;
    }

    this.isSelectingTemplate.set(true);
    this.templateSelectionError.set(null);

    try {
      const template = await window.electronAPI.selectTemplate();

      if (template) {
        this.generatedDocument.set(null);
        this.generationError.set(null);
        this.selectedTemplate.set(template);
      }
    } catch {
      this.templateSelectionError.set('The DOCX template could not be opened.');
    } finally {
      this.isSelectingTemplate.set(false);
    }
  }

  /** Generates and saves a DOCX document with the current form values. */
  protected async onGenerateDocument(): Promise<void> {
    if (!this.selectedTemplate() || !this.hasFormValues() || this.isGenerating()) {
      return;
    }

    this.isGenerating.set(true);
    this.generatedDocument.set(null);
    this.generationError.set(null);

    try {
      const document = await window.electronAPI.generateDocument(
        this.personalForm.getRawValue(),
        this.customFieldControls.getRawValue(),
      );

      if (document) {
        this.generatedDocument.set(document);
      }
    } catch {
      this.generationError.set(
        'The document could not be generated. Check the DOCX template placeholders.',
      );
    } finally {
      this.isGenerating.set(false);
    }
  }

  /** Requests confirmation before clearing non-empty user data. */
  protected async onNewUser(): Promise<void> {
    if (this.hasFormValues()) {
      this.isConfirmingReset.set(true);
      return;
    }

    await this.resetUserWorkspace();
  }

  /** Confirms and performs the pending user reset. */
  protected async onConfirmNewUser(): Promise<void> {
    this.isConfirmingReset.set(false);
    await this.resetUserWorkspace();
  }

  /** Cancels the pending user reset. */
  protected onCancelNewUser(): void {
    this.isConfirmingReset.set(false);
  }

  /** Returns whether the shared form contains at least one non-empty value. */
  protected hasFormValues(): boolean {
    return [...Object.values(this.personalForm.getRawValue()), ...Object.values(this.customFieldControls.getRawValue())]
      .some((value) => value.trim() !== '');
  }

  private async loadCustomFields(): Promise<void> {
    if (!window.electronAPI) {
      this.isLoadingCustomFields.set(false);
      return;
    }

    try {
      this.syncCustomFields(await window.electronAPI.listCustomFields());
    } catch {
      this.customFieldError.set('Custom fields could not be loaded. Please restart the application.');
    } finally {
      this.isLoadingCustomFields.set(false);
    }
  }

  private syncCustomFields(fields: readonly CustomFieldDefinition[]): void {
    const names = new Set(fields.map((field) => field.name));

    for (const name of Object.keys(this.customFieldControls.controls)) {
      if (!names.has(name)) {
        this.customFieldControls.removeControl(name);
      }
    }

    for (const { name } of fields) {
      if (!this.customFieldControls.contains(name)) {
        this.customFieldControls.addControl(name, new FormControl('', { nonNullable: true }));
      }
    }

    this.customFields.set(fields);
  }

  private getCustomFieldValidationError(definition: CustomFieldDefinition): string | null {
    if (!definition.label.trim()) {
      return 'Enter a field label.';
    }

    if (!CUSTOM_FIELD_NAME_PATTERN.test(definition.name)) {
      return 'The placeholder name must start with a letter and contain only letters, numbers, or underscores.';
    }

    const name = definition.name.toLowerCase();
    const standardNames = Object.keys(this.personalForm.controls).map((field) => field.toLowerCase());

    if (
      RESERVED_CUSTOM_FIELD_NAMES.has(name) ||
      standardNames.includes(name) ||
      this.customFields().some((field) => field.name.toLowerCase() === name)
    ) {
      return 'This placeholder name is already used or reserved.';
    }

    return null;
  }

  private closeCreateFieldDialog(): void {
    const dialog = this.createFieldDialog()?.nativeElement;

    if (dialog?.open && typeof dialog.close === 'function') {
      dialog.close();
    } else {
      dialog?.removeAttribute('open');
    }

    this.addFieldButton()?.nativeElement.focus();
  }

  private mergeRecognizedData(documentData: RecognizedDocumentData): void {
    for (const [field, value] of Object.entries(documentData) as [
      RecognizedField,
      string | null,
    ][]) {
      const control = this.personalForm.controls[field];

      if (control.value === '' && value?.trim()) {
        const recognizedValue = value.trim();
        const dateParts = DATE_FIELDS.has(field) ? ISO_DATE_PATTERN.exec(recognizedValue) : null;
        control.setValue(
          dateParts ? `${dateParts[3]}.${dateParts[2]}.${dateParts[1]}` : recognizedValue,
        );
      }
    }
  }

  private async resetUserWorkspace(): Promise<void> {
    try {
      await window.electronAPI?.resetUserSession();
    } catch {
      this.selectionError.set('The current user could not be reset. Please try again.');
      return;
    }

    this.documentType.set('passport');
    this.generatedDocument.set(null);
    this.generationError.set(null);
    this.personalForm.reset();
    this.customFieldControls.reset();
    this.recognitionError.set(null);
    this.selectedDocumentFile.set(null);
    this.selectionError.set(null);
  }
}
