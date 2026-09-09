import type { SelectedImage } from './selected-image.model';

export interface ElectronAPI {
  selectImage(): Promise<SelectedImage | null>;
}
