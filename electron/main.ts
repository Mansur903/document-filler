import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import { readFile } from 'node:fs/promises';
import { basename, join } from 'node:path';

import { SELECT_IMAGE_CHANNEL } from './image-selection';
import type { SelectedImage } from './selected-image.model';

const DEV_SERVER_URL_ARGUMENT = '--dev-server-url=';

void app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  app.quit();
});

ipcMain.handle(SELECT_IMAGE_CHANNEL, async (event): Promise<SelectedImage | null> => {
  const requestingWindow = BrowserWindow.fromWebContents(event.sender);

  if (!requestingWindow || requestingWindow.isDestroyed()) {
    throw new Error('Image selection must be requested by an application window.');
  }

  const result = await dialog.showOpenDialog(requestingWindow, {
    filters: [{ extensions: ['jpg', 'jpeg'], name: 'JPEG images' }],
    properties: ['openFile'],
    title: 'Select passport image',
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }

  const [filePath] = result.filePaths;

  const file = await readFile(filePath);

  return {
    dataUrl: `data:image/jpeg;base64,${file.toString('base64')}`,
    name: basename(filePath),
  };
});

function getDevServerUrl(): string | undefined {
  return process.argv
    .find((argument) => argument.startsWith(DEV_SERVER_URL_ARGUMENT))
    ?.slice(DEV_SERVER_URL_ARGUMENT.length);
}

function createWindow(): void {
  const window = new BrowserWindow({
    height: 720,
    width: 1080,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: join(__dirname, 'preload.js'),
      sandbox: true,
    },
  });

  const devServerUrl = getDevServerUrl();

  if (devServerUrl) {
    void window.loadURL(devServerUrl);
    return;
  }

  void window.loadFile(join(__dirname, '../dist/document-filler/browser/index.html'));
}
