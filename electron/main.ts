import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import { readFile, writeFile } from 'node:fs/promises';
import { basename, extname, join } from 'node:path';

import {
  GENERATE_DOCUMENT_CHANNEL,
  RECOGNIZE_PASSPORT_CHANNEL,
  SELECT_PASSPORT_FILE_CHANNEL,
  SELECT_TEMPLATE_CHANNEL,
} from './ipc.channels';
import type { PassportData } from './models/api.model';
import type {
  GeneratedDocument,
  SelectedPassportFile,
  SelectedTemplate,
} from './models/ui.model';
import {
  generateDocument,
  isPassportFormData,
} from './services/document-generation.service';
import { recognizePassport } from './services/passport-ocr.service';

const DEV_SERVER_URL_ARGUMENT = '--dev-server-url=';
const SUPPORTED_PASSPORT_FILE_EXTENSIONS = new Set(['.jpeg', '.jpg', '.pdf']);
let selectedPassportFilePath: string | null = null;
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
  selectedPassportFilePath = null;
  selectedTemplatePath = null;
  app.quit();
});

ipcMain.handle(
  SELECT_PASSPORT_FILE_CHANNEL,
  async (event): Promise<SelectedPassportFile | null> => {
    const requestingWindow = BrowserWindow.fromWebContents(event.sender);

    if (!requestingWindow || requestingWindow.isDestroyed()) {
      throw new Error('Passport file selection must be requested by an application window.');
    }

    const result = await dialog.showOpenDialog(requestingWindow, {
      filters: [{ extensions: ['jpg', 'jpeg', 'pdf'], name: 'Passport files' }],
      properties: ['openFile'],
      title: 'Select passport file',
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }

    const [filePath] = result.filePaths;
    const extension = extname(filePath).toLowerCase();

    if (!SUPPORTED_PASSPORT_FILE_EXTENSIONS.has(extension)) {
      throw new Error('Only JPG, JPEG, and PDF passport files are supported.');
    }

    const type = extension === '.pdf' ? 'pdf' : 'image';
    const previewDataUrl =
      type === 'image'
        ? `data:image/jpeg;base64,${(await readFile(filePath)).toString('base64')}`
        : null;
    selectedPassportFilePath = filePath;

    return {
      name: basename(filePath),
      previewDataUrl,
      type,
    };
  },
);

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

  if (selectedPassportFilePath === null) {
    throw new Error('The selected passport file is no longer available.');
  }

  return recognizePassport(selectedPassportFilePath);
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
