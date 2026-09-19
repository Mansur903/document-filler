export interface GeneratedDocument {
  readonly name: string;
}

export type PassportFileType = 'image' | 'pdf';

export interface SelectedPassportFile {
  readonly name: string;
  readonly previewDataUrl: string | null;
  readonly type: PassportFileType;
}

export interface SelectedTemplate {
  readonly name: string;
}
