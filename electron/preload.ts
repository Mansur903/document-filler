import { contextBridge, ipcRenderer } from 'electron';

import {
  CREATE_CUSTOM_FIELD_CHANNEL,
  DELETE_CUSTOM_FIELD_CHANNEL,
  GENERATE_DOCUMENT_CHANNEL,
  LIST_CUSTOM_FIELDS_CHANNEL,
  RECOGNIZE_DOCUMENT_CHANNEL,
  RESET_USER_SESSION_CHANNEL,
  SELECT_DOCUMENT_FILE_CHANNEL,
  SELECT_TEMPLATE_CHANNEL,
} from './ipc.channels';
import type { ElectronAPI } from './models/api.model';

const electronAPI: ElectronAPI = {
  createCustomField: (definition) =>
    ipcRenderer.invoke(CREATE_CUSTOM_FIELD_CHANNEL, definition) as ReturnType<
      ElectronAPI['createCustomField']
    >,
  deleteCustomField: (name) =>
    ipcRenderer.invoke(DELETE_CUSTOM_FIELD_CHANNEL, name) as ReturnType<
      ElectronAPI['deleteCustomField']
    >,
  generateDocument: (data, customValues) =>
    ipcRenderer.invoke(GENERATE_DOCUMENT_CHANNEL, data, customValues) as ReturnType<
      ElectronAPI['generateDocument']
    >,
  listCustomFields: () =>
    ipcRenderer.invoke(LIST_CUSTOM_FIELDS_CHANNEL) as ReturnType<ElectronAPI['listCustomFields']>,
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
