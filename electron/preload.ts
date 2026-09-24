import { contextBridge, ipcRenderer } from 'electron';

import {
  GENERATE_DOCUMENT_CHANNEL,
  RECOGNIZE_DOCUMENT_CHANNEL,
  RESET_USER_SESSION_CHANNEL,
  SELECT_DOCUMENT_FILE_CHANNEL,
  SELECT_TEMPLATE_CHANNEL,
} from './ipc.channels';
import type { ElectronAPI } from './models/api.model';

const electronAPI: ElectronAPI = {
  generateDocument: (data) =>
    ipcRenderer.invoke(GENERATE_DOCUMENT_CHANNEL, data) as ReturnType<
      ElectronAPI['generateDocument']
    >,
  recognizeDocument: (documentType) =>
    ipcRenderer.invoke(RECOGNIZE_DOCUMENT_CHANNEL, documentType) as ReturnType<
      ElectronAPI['recognizeDocument']
    >,
  resetUserSession: () =>
    ipcRenderer.invoke(RESET_USER_SESSION_CHANNEL) as ReturnType<ElectronAPI['resetUserSession']>,
  selectDocumentFile: () =>
    ipcRenderer.invoke(SELECT_DOCUMENT_FILE_CHANNEL) as ReturnType<
      ElectronAPI['selectDocumentFile']
    >,
  selectTemplate: () =>
    ipcRenderer.invoke(SELECT_TEMPLATE_CHANNEL) as ReturnType<ElectronAPI['selectTemplate']>,
};

contextBridge.exposeInMainWorld('electronAPI', electronAPI);
