import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';

import type { PassportData } from './models/api.model';
import type { GeneratedDocument, SelectedImage, SelectedTemplate } from './models/ui.model';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule],
  selector: 'tmt-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App {
  protected readonly generatedDocument = signal<GeneratedDocument | null>(null);
  protected readonly generationError = signal<string | null>(null);
  protected readonly hasRecognizedData = signal(false);
  protected readonly isGenerating = signal(false);
  protected readonly isRecognizing = signal(false);
  protected readonly isSelecting = signal(false);
  protected readonly isSelectingTemplate = signal(false);
  protected readonly passportForm = new FormGroup({
    currentNationality: new FormControl('', { nonNullable: true }),
    dateOfBirth: new FormControl('', { nonNullable: true }),
    givenName: new FormControl('', { nonNullable: true }),
    issuedByCountry: new FormControl('', { nonNullable: true }),
    numberOfTravelDocument: new FormControl('', { nonNullable: true }),
    placeOfBirth: new FormControl('', { nonNullable: true }),
    sex: new FormControl('', { nonNullable: true }),
    surname: new FormControl('', { nonNullable: true }),
    validUntil: new FormControl('', { nonNullable: true }),
  });
  protected readonly recognitionError = signal<string | null>(null);
  protected readonly selectedImage = signal<SelectedImage | null>(null);
  protected readonly selectedTemplate = signal<SelectedTemplate | null>(null);
  protected readonly selectionError = signal<string | null>(null);
  protected readonly templateSelectionError = signal<string | null>(null);

  /** Opens the native image picker and stores the selected image for preview. */
  protected async onSelectImage(): Promise<void> {
    if (!window.electronAPI) {
      this.selectionError.set('Image selection is available only in the desktop application.');
      return;
    }

    this.isSelecting.set(true);
    this.selectionError.set(null);

    try {
      const image = await window.electronAPI.selectImage();

      if (image) {
        this.generatedDocument.set(null);
        this.generationError.set(null);
        this.hasRecognizedData.set(false);
        this.passportForm.reset();
        this.recognitionError.set(null);
        this.selectedImage.set(image);
      }
    } catch {
      this.selectionError.set('The image could not be opened. Please try another JPG file.');
    } finally {
      this.isSelecting.set(false);
    }
  }

  /** Recognizes passport fields in the currently selected image. */
  protected async onRecognizePassport(): Promise<void> {
    const image = this.selectedImage();

    if (!image || this.isRecognizing()) {
      return;
    }

    this.isRecognizing.set(true);
    this.recognitionError.set(null);

    try {
      this.fillPassportForm(await window.electronAPI.recognizePassport());
      this.generatedDocument.set(null);
      this.generationError.set(null);
      this.hasRecognizedData.set(true);
    } catch {
      this.recognitionError.set(
        'The passport could not be recognized. Check the image and OCR setup.',
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
    if (!this.hasRecognizedData() || !this.selectedTemplate() || this.isGenerating()) {
      return;
    }

    this.isGenerating.set(true);
    this.generatedDocument.set(null);
    this.generationError.set(null);

    try {
      const document = await window.electronAPI.generateDocument(this.passportForm.getRawValue());

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

  private fillPassportForm(passport: PassportData): void {
    this.passportForm.setValue({
      currentNationality: passport.currentNationality ?? '',
      dateOfBirth: passport.dateOfBirth ?? '',
      givenName: passport.givenName ?? '',
      issuedByCountry: passport.issuedByCountry ?? '',
      numberOfTravelDocument: passport.numberOfTravelDocument ?? '',
      placeOfBirth: passport.placeOfBirth ?? '',
      sex: passport.sex ?? '',
      surname: passport.surname ?? '',
      validUntil: passport.validUntil ?? '',
    });
  }
}
