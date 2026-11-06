export type DocumentFileType = 'image' | 'pdf';
export type DocumentType =
  | 'passport'
  | 'russianBirthCertificate'
  | 'russianInternalPassport'
  | 'russianMarriageCertificate'
  | 'uaeResidencePermit';

export interface CustomFieldDefinition {
  readonly label: string;
  readonly name: string;
}

export interface GeneratedDocument {
  readonly name: string;
}

export interface SelectedDocumentFile {
  readonly name: string;
  readonly previewDataUrl: string | null;
  readonly type: DocumentFileType;
}

export interface SelectedTemplate {
  readonly name: string;
}
