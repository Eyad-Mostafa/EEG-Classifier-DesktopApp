const log = require("electron-log");

// Configure electron-log
log.transports.file.level = "info";
// Optional: format logs for better readability
log.transports.file.format = '[{y}-{m}-{d} {h}:{i}:{s}.{ms}] [{level}] {text}';

// Hook console.log to write to file
console.log = log.log;
Object.assign(console, log.functions);

module.exports = log;