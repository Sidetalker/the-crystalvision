#!/usr/bin/env node
/**
 * Clementine launcher — one command to wake her up.
 *
 *   npm start                        # from the clementine/ folder
 *
 * Starts her brain (server.py), her face (the Svelte webapp), waits for
 * both to come alive, then opens your browser. Everything stays on
 * 127.0.0.1 — nothing leaves this machine. Ctrl+C stops it all.
 *
 * Flags after `npm start --` are passed to server.py, e.g.:
 *   npm start -- --profile Crystal --model qwen2.5:7b
 */

import { spawn, spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const webappDir = join(root, 'webapp');

const API_PORT = 5000;
const WEB_PORT = 5174;
const WEB_URL = `http://127.0.0.1:${WEB_PORT}`;

const serverArgs = process.argv.slice(2);
const children = [];
let shuttingDown = false;

function log(msg) {
  console.log(`[clementine] ${msg}`);
}

function findPython() {
  // Explicit override first: CLEMENTINE_PYTHON=/path/to/python npm start
  const candidates = [process.env.CLEMENTINE_PYTHON, 'python3', 'python'].filter(Boolean);
  // Prefer an interpreter that already has Flask installed.
  for (const cmd of candidates) {
    const probe = spawnSync(cmd, ['-c', 'import flask'], { stdio: 'ignore' });
    if (probe.status === 0) return cmd;
  }
  // Otherwise fall back to any working python and let server.py explain.
  for (const cmd of candidates) {
    const probe = spawnSync(cmd, ['--version'], { stdio: 'ignore' });
    if (probe.status === 0) return cmd;
  }
  return null;
}

function shutdown(code = 0) {
  if (shuttingDown) return;
  shuttingDown = true;
  log('saying goodnight...');
  for (const child of children) {
    if (!child.killed) child.kill('SIGTERM');
  }
  // Give the children a moment to exit cleanly.
  setTimeout(() => process.exit(code), 500);
}

process.on('SIGINT', () => shutdown(0));
process.on('SIGTERM', () => shutdown(0));

function run(name, cmd, args, cwd) {
  const child = spawn(cmd, args, { cwd, stdio: 'inherit', shell: false });
  child.on('exit', (code) => {
    if (!shuttingDown) {
      log(`${name} stopped (exit ${code ?? 'signal'}) — shutting everything down.`);
      shutdown(code ?? 0);
    }
  });
  children.push(child);
  return child;
}

async function waitForHttp(url, label, tries = 60, delayMs = 500) {
  for (let i = 0; i < tries; i++) {
    if (shuttingDown) return false;
    try {
      await fetch(url, { signal: AbortSignal.timeout(1500) });
      return true; // any HTTP response means the port is alive
    } catch {
      await new Promise((r) => setTimeout(r, delayMs));
    }
  }
  log(`gave up waiting for ${label} at ${url}`);
  return false;
}

function openBrowser(url) {
  const platform = process.platform;
  let cmd, args;
  if (platform === 'darwin') {
    cmd = 'open';
    args = [url];
  } else if (platform === 'win32') {
    cmd = 'cmd';
    args = ['/c', 'start', '', url];
  } else {
    cmd = 'xdg-open';
    args = [url];
  }
  const child = spawn(cmd, args, { stdio: 'ignore', detached: true });
  child.on('error', () => log(`couldn't open a browser — visit ${url} yourself`));
  child.unref();
}

async function main() {
  const python = findPython();
  if (!python) {
    console.error('[clementine] python3 not found on PATH. Install Python 3 first.');
    process.exit(1);
  }

  // Install webapp dependencies on first run.
  if (!existsSync(join(webappDir, 'node_modules'))) {
    log('first run — installing webapp dependencies...');
    const install = spawnSync('npm', ['install'], { cwd: webappDir, stdio: 'inherit' });
    if (install.status !== 0) {
      console.error('[clementine] npm install failed in webapp/.');
      process.exit(1);
    }
  }

  log('waking her brain (server.py)...');
  run('brain', python, ['server.py', ...serverArgs], root);

  log('waking her face (webapp)...');
  run('face', 'npm', ['run', 'dev'], webappDir);

  const [apiUp, webUp] = await Promise.all([
    waitForHttp(`http://127.0.0.1:${API_PORT}/api/status`, 'her brain'),
    waitForHttp(WEB_URL, 'her face')
  ]);

  if (webUp) {
    log(`she's awake — opening ${WEB_URL}`);
    if (!apiUp) log('note: her brain is not answering yet (is Ollama running?)');
    openBrowser(WEB_URL);
  }
}

main();
