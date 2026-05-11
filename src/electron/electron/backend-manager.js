const { spawn, exec } = require("child_process");
const log = require("./logger");
const path = require("path");

let backendProcess = null;

function startBackend(port) {
  const backendPath = path.join(process.resourcesPath, "backend", "backend.exe");
  log.info(`Launching Backend from: ${backendPath} on port ${port}`);

  backendProcess = spawn(backendPath, [`--port=${port}`], {
    stdio: 'pipe',
    // Force UTF-8 to prevent 'charmap' codec errors on Windows
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' } 
  });

  backendProcess.stdout.on('data', (data) => {
    log.info(`[Python]: ${data.toString().trim()}`);
  });

  backendProcess.stderr.on('data', (data) => {
    log.error(`[Python Error]: ${data.toString().trim()}`);
  });

  backendProcess.on('close', (code) => {
    log.info(`Backend process exited with code ${code}`);
    backendProcess = null;
  });
}

function killBackend() {
  if (!backendProcess) return;

  log.info(`Killing Backend (PID: ${backendProcess.pid})...`);

  if (process.platform === "win32") {
    // Windows: Force kill by PID and kill children (/T)
    exec(`taskkill /pid ${backendProcess.pid} /f /t`, (err) => {
      if (err) log.error(`Failed to taskkill backend: ${err}`);
    });
  } else {
    // Mac/Linux: Standard kill
    backendProcess.kill('SIGKILL');
  }
  
  backendProcess = null;
}

module.exports = { startBackend, killBackend };