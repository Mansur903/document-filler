import { contextBridge, ipcRenderer } from 'electron';

import {
  GENERATE_DOCUMENT_CHANNEL,
  RECOGNIZE_PASSPORT_CHANNEL,
  SELECT_PASSPORT_FILE_CHANNEL,
  SELECT_TEMPLATE_CHANNEL,
} from './ipc.channels';
import type { ElectronAPI } from './models/api.model';

const electronAPI: ElectronAPI = {
  generateDocument: (data) =>
    ipcRenderer.invoke(GENERATE_DOCUMENT_CHANNEL, data) as ReturnType<
      ElectronAPI['generateDocument']
    >,
  recognizePassport: () =>
    ipcRenderer.invoke(RECOGNIZE_PASSPORT_CHANNEL) as ReturnType<ElectronAPI['recognizePassport']>,
  selectPassportFile: () =>
    ipcRenderer.invoke(SELECT_PASSPORT_FILE_CHANNEL) as ReturnType<
      ElectronAPI['selectPassportFile']
    >,
  selectTemplate: () =>
    ipcRenderer.invoke(SELECT_TEMPLATE_CHANNEL) as ReturnType<ElectronAPI['selectTemplate']>,
};

contextBridge.exposeInMainWorld('electronAPI', electronAPI);
