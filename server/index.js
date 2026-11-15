import 'dotenv/config';
import express from 'express';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer as createViteServer } from 'vite';
import app from './app.js';
import { connectDatabase } from './db.js';

const ROOT = fileURLToPath(new URL('../', import.meta.url));
const isDev = process.argv.includes('--dev');
const port = Number(process.env.PORT || 8501);

try {
  const connected = await connectDatabase();
  console.log(connected ? 'MongoDB connected.' : 'MongoDB is not configured; reading the local processed CSV snapshot.');
} catch (error) {
  console.warn(`MongoDB unavailable; using CSV fallback (${error.message}).`);
}

if (isDev) {
  const vite = await createViteServer({
    configFile: resolve(ROOT, 'vite.config.js'),
    server: { middlewareMode: true },
    appType: 'custom',
  });
  app.use(vite.middlewares);
  app.get(/.*/, async (req, res, next) => {
    if (req.path.startsWith('/api/')) return next();
    try {
      const template = await readFile(resolve(ROOT, 'client/index.html'), 'utf8');
      const html = await vite.transformIndexHtml(req.originalUrl, template);
      return res.status(200).type('html').send(html);
    } catch (error) {
      vite.ssrFixStacktrace(error);
      return next(error);
    }
  });
  app.use((error, req, res, next) => {
    vite.ssrFixStacktrace(error);
    next(error);
  });
} else {
  app.use(express.static(resolve(ROOT, 'client/dist')));
  app.get(/.*/, (req, res, next) => {
    if (req.path.startsWith('/api/')) return next();
    return res.sendFile(resolve(ROOT, 'client/dist/index.html'));
  });
}

app.listen(port, process.env.HOST || '127.0.0.1', () => {
  console.log(`DT-CARGO web app listening at http://127.0.0.1:${port}`);
});
