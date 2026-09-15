import { contextBridge, ipcRenderer } from 'electron';

import type { ElectronAPI } from './models/api.model';

const SELECT_IMAGE_CHANNEL = 'dialog:select-image';
const RECOGNIZE_PASSPORT_CHANNEL = 'passport:recognize';

const electronAPI: ElectronAPI = {
  recognizePassport: () =>
    ipcRenderer.invoke(RECOGNIZE_PASSPORT_CHANNEL) as ReturnType<
      ElectronAPI['recognizePassport']
    >,
  selectImage: () =>
    ipcRenderer.invoke(SELECT_IMAGE_CHANNEL) as ReturnType<ElectronAPI['selectImage']>,
};

contextBridge.exposeInMainWorld('electronAPI', electronAPI);
