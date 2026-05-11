const { BrowserWindow, shell, app } = require("electron");
const path = require("path");
const log = require("./logger");
const { isDev } = require("./utils");

let mainWindow = null;
let splashWindow = null;

function createSplash() {
  splashWindow = new BrowserWindow({
    width: 500,
    height: 300,
    frame: false,
    alwaysOnTop: true,
    transparent: true,
    center: true, // Ensure it appears in the center
    resizable: false, // Prevent resizing the splash
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
    icon: path.join(__dirname, "..", "icon.ico"),
  });

  splashWindow.loadFile(path.join(__dirname, "..", "splash.html"));
}

function createMainWindow(apiPort) {
  // 1. Create the window
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    icon: path.join(__dirname, "..", "icon.ico"),
    show: false,
    fullscreen: false,
    frame: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: !isDev,
      devTools: isDev,
      zoomFactor: 1.0,
      preload: path.join(__dirname, "preload.js"),
    },
    autoHideMenuBar: true,
  });

  mainWindow.setMenu(null);

  // 2. Configure External Links
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https:') || url.startsWith('http:')) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  // 3. Security & UX Shortcuts (Zoom/Reload Block)
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.control) {
      const key = input.key.toLowerCase();
      if (key === '+' || key === '-' || key === '=') event.preventDefault();
      if (key === 'r') event.preventDefault();
      if (input.shift && key === 'i') event.preventDefault();
    }
  });

  mainWindow.webContents.setVisualZoomLevelLimits(1, 1);

  // 4. Load Content
  const indexPath = path.join(__dirname, "..", "dist", "eeg-classifier-angular", "index.html");
  const loadUrl = `file://${indexPath}?apiPort=${apiPort}`;
  log.info(`Loading UI from: ${loadUrl}`);

  mainWindow.loadURL(loadUrl);

  // 5. Handle Show (With Maximize)
  mainWindow.once('ready-to-show', () => {
    log.info("Main Window Ready. Hiding Splash.");

    if (splashWindow) {
      splashWindow.close();
      splashWindow = null;
    }


    mainWindow.maximize();

    mainWindow.show();
    mainWindow.focus();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  return mainWindow;
}

function focusMainWindow() {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.focus();
  }
}

module.exports = { createSplash, createMainWindow, focusMainWindow };