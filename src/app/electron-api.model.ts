import type { SelectedImage } from './selected-image.model';

export type { SelectedImage } from './selected-image.model';

export interface ElectronAPI {
  selectImage(): Promise<SelectedImage | null>;
}

declare global {
  interface Window {
    readonly electronAPI: ElectronAPI;
  }
}
