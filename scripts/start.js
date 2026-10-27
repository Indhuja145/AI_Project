const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const isWindows = process.platform === 'win32';
const localPython = isWindows
  ? path.join(root, '.venv', 'Scripts', 'python.exe')
  : path.join(root, '.venv', 'bin', 'python');

const candidates = [];
if (fs.existsSync(localPython)) candidates.push({ command: localPython, args: [] });
if (isWindows) {
  candidates.push({ command: 'py', args: [] });
  candidates.push({ command: 'python', args: [] });
} else {
  candidates.push({ command: 'python3', args: [] });
  candidates.push({ command: 'python', args: [] });
}

function tryPython(index) {
  if (index >= candidates.length) {
    console.error('\nPython or the project dependencies are not ready. Run once:');
    console.error('  python -m venv .venv');
    console.error('  .venv\\Scripts\\activate');
    console.error('  python -m pip install -r requirements.txt\n');
    process.exit(1);
  }

  const candidate = candidates[index];
  const check = spawn(candidate.command, [...candidate.args, '-c', 'import uvicorn'], {
    cwd: root,
    stdio: 'ignore',
    windowsHide: true,
  });

  check.on('error', () => tryPython(index + 1));
  check.on('exit', (code) => {
    if (code !== 0) return tryPython(index + 1);

    const server = spawn(candidate.command, [
      ...candidate.args,
      '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000',
    ], {
      cwd: root,
      stdio: 'inherit',
      windowsHide: false,
    });

    server.on('error', (error) => {
      console.error(`Unable to start the backend: ${error.message}`);
      process.exit(1);
    });
    server.on('exit', (code, signal) => {
      if (signal) process.kill(process.pid, signal);
      else process.exit(code ?? 1);
    });
  });
}

tryPython(0);
