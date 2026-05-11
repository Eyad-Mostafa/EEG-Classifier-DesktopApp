const path = require("path");
const net = require("net");
const { app } = require("electron");

const isDev = !app.isPackaged;

function getBackendPath() {
  const isWindows = process.platform === "win32";
  const binaryName = isWindows ? "backend.exe" : "backend";

  if (isDev) {
    return path.join(__dirname, "..", "backend-bin", binaryName);
  } else {
    return path.join(process.resourcesPath, binaryName);
  }
}

function findFreePort(startPort) {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(startPort, () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
    server.on('error', (err) => {
      if (err.code === 'EADDRINUSE') {
        resolve(findFreePort(startPort + 1));
      } else {
        reject(err);
      }
    });
  });
}

module.exports = { getBackendPath, findFreePort, isDev };