import type {
  DocumentType,
  GeneratedDocument,
  SelectedDocumentFile,
  SelectedTemplate,
} from './ui.model';

export interface ElectronAPI {
  generateDocument(data: PersonalFormData): Promise<GeneratedDocument | null>;
  recognizeDocument(documentType: DocumentType): Promise<RecognizedDocumentData>;
  resetUserSession(): Promise<void>;
  selectDocumentFile(): Promise<SelectedDocumentFile | null>;
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

export interface ResidencePermitData {
  readonly currentOccupation: string | null;
  readonly employer: string | null;
  readonly residencepermitID: string | null;
  readonly visaID: string | null;
  readonly visaValidUntil: string | null;
}

export type RecognizedDocumentData = PassportData | ResidencePermitData;

export interface PersonalFormData {
  readonly address: string;
  readonly currentNationality: string;
  readonly currentOccupation: string;
  readonly dateOfBirth: string;
  readonly dateOfIssue: string;
  readonly email: string;
  readonly employer: string;
  readonly givenName: string;
  readonly issuedByCountry: string;
  readonly numberOfTravelDocument: string;
  readonly phone: string;
  readonly placeOfBirth: string;
  readonly residencepermitID: string;
  readonly sex: string;
  readonly surname: string;
  readonly validUntil: string;
  readonly visaID: string;
  readonly visaValidUntil: string;
}

declare global {
  interface Window {
    readonly electronAPI: ElectronAPI;
  }
}
