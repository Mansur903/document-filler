import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import { readFile, writeFile } from 'node:fs/promises';
import { basename, extname, join } from 'node:path';

import {
  GENERATE_DOCUMENT_CHANNEL,
  RECOGNIZE_PASSPORT_CHANNEL,
  SELECT_IMAGE_CHANNEL,
  SELECT_TEMPLATE_CHANNEL,
} from './ipc.channels';
import type { PassportData } from './models/api.model';
import type { GeneratedDocument, SelectedImage, SelectedTemplate } from './models/ui.model';
import {
  generateDocument,
  isPassportFormData,
} from './services/document-generation.service';
import { recognizePassport } from './services/passport-ocr.service';

const DEV_SERVER_URL_ARGUMENT = '--dev-server-url=';
let selectedImagePath: string | null = null;
let selectedTemplatePath: string | null = null;

void app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  selectedImagePath = null;
  selectedTemplatePath = null;
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
  selectedImagePath = filePath;

  return {
    dataUrl: `data:image/jpeg;base64,${file.toString('base64')}`,
    name: basename(filePath),
  };
});

ipcMain.handle(SELECT_TEMPLATE_CHANNEL, async (event): Promise<SelectedTemplate | null> => {
  const requestingWindow = BrowserWindow.fromWebContents(event.sender);

  if (!requestingWindow || requestingWindow.isDestroyed()) {
    throw new Error('Template selection must be requested by an application window.');
  }

  const result = await dialog.showOpenDialog(requestingWindow, {
    filters: [{ extensions: ['docx'], name: 'Word documents' }],
    properties: ['openFile'],
    title: 'Select DOCX template',
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }

  const [templatePath] = result.filePaths;
  selectedTemplatePath = templatePath;

  return { name: basename(templatePath) };
});

ipcMain.handle(RECOGNIZE_PASSPORT_CHANNEL, async (event): Promise<PassportData> => {
  const requestingWindow = BrowserWindow.fromWebContents(event.sender);

  if (!requestingWindow || requestingWindow.isDestroyed()) {
    throw new Error('Passport recognition must be requested by an application window.');
  }

  if (selectedImagePath === null) {
    throw new Error('The selected image is no longer available.');
  }

  if (app.isPackaged) {
    throw new Error('The packaged OCR runtime is not configured yet.');
  }

  return recognizePassport(app.getAppPath(), selectedImagePath);
});

ipcMain.handle(
  GENERATE_DOCUMENT_CHANNEL,
  async (event, data: unknown): Promise<GeneratedDocument | null> => {
    const requestingWindow = BrowserWindow.fromWebContents(event.sender);

    if (!requestingWindow || requestingWindow.isDestroyed()) {
      throw new Error('Document generation must be requested by an application window.');
    }

    if (selectedTemplatePath === null) {
      throw new Error('Select a DOCX template before generating a document.');
    }

    if (!isPassportFormData(data)) {
      throw new Error('The passport form contains invalid data.');
    }

    const document = await generateDocument(selectedTemplatePath, data);
    const templateExtension = extname(selectedTemplatePath);
    const defaultName = `${basename(selectedTemplatePath, templateExtension)}-filled.docx`;
    const result = await dialog.showSaveDialog(requestingWindow, {
      defaultPath: defaultName,
      filters: [{ extensions: ['docx'], name: 'Word documents' }],
      title: 'Save filled document',
    });

    if (result.canceled || !result.filePath) {
      return null;
    }

    const outputPath = result.filePath.toLowerCase().endsWith('.docx')
      ? result.filePath
      : `${result.filePath}.docx`;
    await writeFile(outputPath, document);

    return { name: basename(outputPath) };
  },
);

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
