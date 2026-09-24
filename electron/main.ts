import { app, BrowserWindow, dialog, ipcMain } from 'electron';
import { readFile, writeFile } from 'node:fs/promises';
import { basename, extname, join } from 'node:path';

import {
  GENERATE_DOCUMENT_CHANNEL,
  RECOGNIZE_DOCUMENT_CHANNEL,
  RESET_USER_SESSION_CHANNEL,
  SELECT_DOCUMENT_FILE_CHANNEL,
  SELECT_TEMPLATE_CHANNEL,
} from './ipc.channels';
import type { RecognizedDocumentData } from './models/api.model';
import type {
  DocumentType,
  GeneratedDocument,
  SelectedDocumentFile,
  SelectedTemplate,
} from './models/ui.model';
import { generateDocument, isPersonalFormData } from './services/document-generation.service';
import { recognizeDocument } from './services/passport-ocr.service';

const DEV_SERVER_URL_ARGUMENT = '--dev-server-url=';
const DOCUMENT_TYPES: readonly DocumentType[] = ['passport', 'uaeResidencePermit'];
const SUPPORTED_DOCUMENT_FILE_EXTENSIONS = new Set(['.jpeg', '.jpg', '.pdf', '.png']);
let selectedDocumentFilePath: string | null = null;
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
  selectedDocumentFilePath = null;
  selectedTemplatePath = null;
  app.quit();
});

ipcMain.handle(
  SELECT_DOCUMENT_FILE_CHANNEL,
  async (event): Promise<SelectedDocumentFile | null> => {
    const requestingWindow = BrowserWindow.fromWebContents(event.sender);

    if (!requestingWindow || requestingWindow.isDestroyed()) {
      throw new Error('Document file selection must be requested by an application window.');
    }

    const result = await dialog.showOpenDialog(requestingWindow, {
      filters: [{ extensions: ['jpg', 'jpeg', 'png', 'pdf'], name: 'Document files' }],
      properties: ['openFile'],
      title: 'Select document file',
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }

    const [filePath] = result.filePaths;
    const extension = extname(filePath).toLowerCase();

    if (!SUPPORTED_DOCUMENT_FILE_EXTENSIONS.has(extension)) {
      throw new Error('Only JPG, JPEG, PNG, and PDF document files are supported.');
    }

    const type = extension === '.pdf' ? 'pdf' : 'image';
    const mediaType = extension === '.png' ? 'image/png' : 'image/jpeg';
    const previewDataUrl =
      type === 'image'
        ? `data:${mediaType};base64,${(await readFile(filePath)).toString('base64')}`
        : null;
    selectedDocumentFilePath = filePath;

    return {
      name: basename(filePath),
      previewDataUrl,
      type,
    };
  },
);

ipcMain.handle(RESET_USER_SESSION_CHANNEL, (event): void => {
  const requestingWindow = BrowserWindow.fromWebContents(event.sender);

  if (!requestingWindow || requestingWindow.isDestroyed()) {
    throw new Error('User reset must be requested by an application window.');
  }

  selectedDocumentFilePath = null;
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

ipcMain.handle(
  RECOGNIZE_DOCUMENT_CHANNEL,
  async (event, documentType: unknown): Promise<RecognizedDocumentData> => {
    const requestingWindow = BrowserWindow.fromWebContents(event.sender);

    if (!requestingWindow || requestingWindow.isDestroyed()) {
      throw new Error('Document recognition must be requested by an application window.');
    }

    if (!isDocumentType(documentType)) {
      throw new Error('The requested document type is not supported.');
    }

    if (selectedDocumentFilePath === null) {
      throw new Error('The selected document file is no longer available.');
    }

    return recognizeDocument(selectedDocumentFilePath, documentType);
  },
);

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

    if (!isPersonalFormData(data)) {
      throw new Error('The personal form contains invalid data.');
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

function isDocumentType(value: unknown): value is DocumentType {
  return typeof value === 'string' && DOCUMENT_TYPES.includes(value as DocumentType);
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
