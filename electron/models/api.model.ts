import type {
  CustomFieldDefinition,
  DocumentType,
  GeneratedDocument,
  SelectedDocumentFile,
  SelectedTemplate,
} from './ui.model';
import type { BirthCertificateField, MarriageCertificateField } from './certificate-fields';

export interface ElectronAPI {
  createCustomField(definition: CustomFieldDefinition): Promise<readonly CustomFieldDefinition[]>;
  deleteCustomField(name: string): Promise<readonly CustomFieldDefinition[]>;
  generateDocument(
    data: PersonalFormData,
    customValues: Readonly<Record<string, string>>,
  ): Promise<GeneratedDocument | null>;
  listCustomFields(): Promise<readonly CustomFieldDefinition[]>;
  recognizeDocument(documentType: DocumentType): Promise<RecognizedDocumentData>;
  resetUserSession(): Promise<void>;
  selectDocumentFile(): Promise<SelectedDocumentFile | null>;
  selectTemplate(): Promise<SelectedTemplate | null>;
}

export interface PassportData {
  readonly authority: string | null;
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

export interface InternalPassportData {
  readonly authority: string | null;
  readonly dateOfBirth: string | null;
  readonly dateOfIssue: string | null;
  readonly givenName: string | null;
  readonly internalPassportNumber: string | null;
  readonly internalPassportSeries: string | null;
  readonly patronymic: string | null;
  readonly placeOfBirth: string | null;
  readonly sex: string | null;
  readonly subdivisionCode: string | null;
  readonly surname: string | null;
}

export interface ResidencePermitData {
  readonly currentOccupation: string | null;
  readonly employer: string | null;
  readonly residencepermitID: string | null;
  readonly visaID: string | null;
  readonly visaValidUntil: string | null;
}

export type BirthCertificateData = Readonly<Record<BirthCertificateField, string | null>>;
export type MarriageCertificateData = Readonly<Record<MarriageCertificateField, string | null>>;

export type RecognizedDocumentData =
  | PassportData
  | InternalPassportData
  | ResidencePermitData
  | BirthCertificateData
  | MarriageCertificateData;

export interface PersonalFormData extends Readonly<Record<BirthCertificateField | MarriageCertificateField, string>> {
  readonly address: string;
  readonly authority: string;
  readonly currentNationality: string;
  readonly currentOccupation: string;
  readonly dateOfBirth: string;
  readonly dateOfIssue: string;
  readonly email: string;
  readonly employer: string;
  readonly givenName: string;
  readonly internalPassportNumber: string;
  readonly internalPassportSeries: string;
  readonly issuedByCountry: string;
  readonly numberOfTravelDocument: string;
  readonly phone: string;
  readonly patronymic: string;
  readonly placeOfBirth: string;
  readonly residencepermitID: string;
  readonly sex: string;
  readonly surname: string;
  readonly subdivisionCode: string;
  readonly validUntil: string;
  readonly visaID: string;
  readonly visaValidUntil: string;
}
