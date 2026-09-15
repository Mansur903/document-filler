import type { SelectedImage } from './ui.model';

export interface ElectronAPI {
  recognizePassport(): Promise<PassportData>;
  selectImage(): Promise<SelectedImage | null>;
}

export interface PassportData {
  readonly currentNationality: string | null;
  readonly dateOfBirth: string | null;
  readonly givenName: string | null;
  readonly issuedByCountry: string | null;
  readonly numberOfTravelDocument: string | null;
  readonly placeOfBirth: string | null;
  readonly sex: string | null;
  readonly surname: string | null;
  readonly validUntil: string | null;
}
