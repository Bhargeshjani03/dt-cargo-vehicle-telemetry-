import { existsSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const candidates = [
  process.env.PYTHON_BIN?.trim(),
  resolve(root, process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python'),
  'python3',
  'python',
].filter(Boolean);
const python = candidates.find((candidate) => candidate === 'python3' || candidate === 'python' || existsSync(candidate));

if (!python) {
  console.error('Python was not found. Set PYTHON_BIN or create the project .venv first.');
  process.exit(1);
}

const result = spawnSync(python, process.argv.slice(2), { cwd: root, stdio: 'inherit' });
if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);
