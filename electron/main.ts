import { app, BrowserWindow } from 'electron';
import { join } from 'node:path';

const DEV_SERVER_URL_ARGUMENT = '--dev-server-url=';

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
