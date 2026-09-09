import { contextBridge, ipcRenderer } from 'electron';

import type { ElectronAPI } from './electron-api.model';

const SELECT_IMAGE_CHANNEL = 'dialog:select-image';

const electronAPI: ElectronAPI = {
  selectImage: () =>
    ipcRenderer.invoke(SELECT_IMAGE_CHANNEL) as ReturnType<ElectronAPI['selectImage']>,
};

contextBridge.exposeInMainWorld('electronAPI', electronAPI);
