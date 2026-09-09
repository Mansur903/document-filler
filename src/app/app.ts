import { ChangeDetectionStrategy, Component, signal } from '@angular/core';

import type { SelectedImage } from './electron-api.model';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [],
  selector: 'tmt-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App {
  protected readonly isSelecting = signal(false);
  protected readonly selectedImage = signal<SelectedImage | null>(null);
  protected readonly selectionError = signal<string | null>(null);

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
        this.selectedImage.set(image);
      }
    } catch {
      this.selectionError.set('The image could not be opened. Please try another JPG file.');
    } finally {
      this.isSelecting.set(false);
    }
  }
}
