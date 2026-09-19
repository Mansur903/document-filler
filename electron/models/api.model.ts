import type { GeneratedDocument, SelectedPassportFile, SelectedTemplate } from './ui.model';

export interface ElectronAPI {
  generateDocument(data: PassportFormData): Promise<GeneratedDocument | null>;
  recognizePassport(): Promise<PassportData>;
  selectPassportFile(): Promise<SelectedPassportFile | null>;
  selectTemplate(): Promise<SelectedTemplate | null>;
}

export interface PassportData {
  readonly currentNationality: string | null;
  readonly dateOfBirth: string | null;
  readonly dateOfIssue: string | null;
  readonly givenName: string | null;
  readonly issuedByCountry: string | null;
  readonly numberOfTravelDocument: string | null;
  readonly placeOfBirth: string | null;
  readonly sex: string | null;
  readonly surname: string | null;
  readonly validUntil: string | null;
}

export interface PassportFormData {
  readonly currentNationality: string;
  readonly dateOfBirth: string;
  readonly dateOfIssue: string;
  readonly givenName: string;
  readonly issuedByCountry: string;
  readonly numberOfTravelDocument: string;
  readonly placeOfBirth: string;
  readonly sex: string;
  readonly surname: string;
  readonly validUntil: string;
}
