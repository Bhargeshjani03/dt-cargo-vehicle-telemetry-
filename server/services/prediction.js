import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('../../', import.meta.url));

export function runDurationPrediction(payload) {
  const python = process.env.PYTHON_BIN?.trim() || [
    resolve(ROOT, process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python'),
    'python3',
  ].find((candidate) => candidate === 'python3' || candidate === 'python' || existsSync(candidate));
  const script = resolve(ROOT, 'src/tour_duration/predict_cli.py');
  return new Promise((resolveResult, reject) => {
    const child = spawn(python, [script], { cwd: ROOT, stdio: ['pipe', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    const timeout = setTimeout(() => child.kill('SIGTERM'), 12000);
    child.stdout.setEncoding('utf8').on('data', (chunk) => { stdout += chunk; });
    child.stderr.setEncoding('utf8').on('data', (chunk) => { stderr += chunk; });
    child.on('error', (error) => { clearTimeout(timeout); reject(error); });
    child.on('close', (code) => {
      clearTimeout(timeout);
      if (code !== 0) return reject(new Error(stderr || 'Duration model inference failed.'));
      try { resolveResult(JSON.parse(stdout)); }
      catch { reject(new Error('The duration model returned an unreadable response.')); }
    });
    child.stdin.end(JSON.stringify(payload));
  });
}
