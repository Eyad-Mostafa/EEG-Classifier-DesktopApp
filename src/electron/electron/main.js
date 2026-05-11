const { app, dialog, ipcMain, shell } = require("electron");
const log = require("./logger");
const { findFreePort } = require("./utils");
const { startBackend, killBackend } = require("./backend-manager");
const { createSplash, createMainWindow, focusMainWindow } = require("./window-manager");
const fs = require("fs");
const os = require("os");
const path = require("path");
const http = require("http");

// --- GLOBAL CONFIG ---
// We use this prefix to identify OUR files in the temp folder
const TEMP_FILE_PREFIX = "eeg_app_manual_";
const tempFilesToDelete = []; // Track current session files

// --- HELPER: Smart Cleanup Function ---
// Scans the temp folder for ANY file starting with our prefix and deletes it.
function performStartupCleanup() {
  const tempDir = os.tmpdir();

  fs.readdir(tempDir, (err, files) => {
    if (err) {
      log.warn(`Cleanup: Could not read temp dir: ${err.message}`);
      return;
    }

    // Filter for files that look like "eeg_app_manual_..."
    const myFiles = files.filter(f => f.startsWith(TEMP_FILE_PREFIX) && f.endsWith(".pdf"));

    if (myFiles.length > 0) {
      log.info(`Cleanup: Found ${myFiles.length} old temp files from previous sessions. Deleting...`);
    }

    myFiles.forEach(file => {
      const fullPath = path.join(tempDir, file);
      try {
        fs.unlink(fullPath, (err) => {
          if (!err) {
            log.info(`Cleanup: Deleted old file ${file}`);
          }
        });
      } catch (e) {
        // Ignore errors (e.g., if file is STILL locked by a user, we just try again next time)
      }
    });
  });
}

// --- HELPER: Wait for Backend ---
function waitForBackend(port) {
  return new Promise((resolve, reject) => {
    const url = `http://127.0.0.1:${port}/api/health`;
    const maxRetries = 240;
    let attempts = 0;

    log.info(`Waiting for backend at ${url}...`);

    const check = () => {
      attempts++;
      const req = http.get(url, (res) => {
        if (res.statusCode === 200) {
          log.info(`Backend is ready after ${(attempts * 0.5).toFixed(1)}s!`);
          resolve();
        } else {
          setTimeout(check, 500);
        }
      });

      req.on('error', (err) => {
        if (attempts >= maxRetries) {
          reject(new Error(`Backend failed to start after 2 minutes. Last error: ${err.message}`));
        } else {
          setTimeout(check, 500);
        }
      });

      req.end();
    };

    check();
  });
}

// --- IPC HANDLER ---
ipcMain.handle('open-method-pdf', async (event, sourceFilename, displayName) => {
  try {
    const sourcePath = path.join(
      __dirname,
      "..",
      "dist",
      "eeg-classifier-angular",
      "assets",
      "algorithms-docs",
      sourceFilename
    );

    const tempDir = os.tmpdir();

    // 1. Construct the nice filename
    // Result: C:\Users\Temp\eeg_app_manual_Bandpass_Filter_Manual.pdf
    // We attach the prefix so our cleanup script knows it's ours.
    let finalFileName = `${TEMP_FILE_PREFIX}${displayName}`;
    let destPath = path.join(tempDir, finalFileName);

    // 2. SMART CONFLICT HANDLING
    // If the file exists and is locked (user has it open), we can't overwrite it.
    // We try to append a number until we find a free name.
    let counter = 1;
    while (true) {
      try {
        // Try to open/write to check if it's locked
        // We use 'r+' (read/write) to test if we have permission
        if (fs.existsSync(destPath)) {
          // Try to delete it first. If it's locked, this throws an error.
          await fs.promises.unlink(destPath);
        }
        break; // If delete worked (or file didn't exist), we are free to use this name!
      } catch (err) {
        // If error is EBUSY or EPERM, the file is locked by PDF Viewer.
        // So we change the name and try again.
        log.warn(`File ${finalFileName} is locked. Trying next available name...`);
        finalFileName = `${TEMP_FILE_PREFIX}${path.parse(displayName).name}_${counter}.pdf`;
        destPath = path.join(tempDir, finalFileName);
        counter++;
      }
    }

    log.info(`Copying PDF to ${destPath}`);

    await fs.promises.copyFile(sourcePath, destPath);

    // Track for cleanup
    if (!tempFilesToDelete.includes(destPath)) {
      tempFilesToDelete.push(destPath);
    }

    const result = await shell.openPath(destPath);

    if (result) {
      throw new Error(result);
    }
    return true;

  } catch (error) {
    log.error("Error in open-method-pdf:", error);
    dialog.showErrorBox("Manual Error", `Could not open manual.\n\nDetails: ${error.message}`);
    throw error;
  }
});

// --- APP LIFECYCLE ---
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    focusMainWindow();
  });

  app.whenReady().then(async () => {
    // STEP 1: Run Cleanup immediately on startup
    performStartupCleanup();

    createSplash();

    try {
      const port = await findFreePort(8000);
      log.info(`Found free port: ${port}`);

      startBackend(port);
      await waitForBackend(port);
      createMainWindow(port);

    } catch (err) {
      log.error("Critical Startup Error:", err);
      dialog.showErrorBox("Startup Failed", "Error: " + err.message);
      app.quit();
    }
  });
}

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  killBackend();

  // 🧹 STEP 2: Try to clean up current session files on exit
  log.info("Cleaning up current session PDF files...");
  tempFilesToDelete.forEach((filePath) => {
    try {
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
        log.info(`Deleted temp file: ${filePath}`);
      }
    } catch (err) {
      log.warn(`Could not delete ${filePath} on exit: ${err.message}`);
    }
  });
});