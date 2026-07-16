/* Copies the Interval Timer's runtime web assets into ./www so Capacitor can
   bundle them. The web app is a single-file static app with no build step, so
   this is just a whitelist copy — run automatically by `npm run sync`. */
import { mkdirSync, copyFileSync, rmSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const srcDir = join(here, '..', 'boxing-timer');
const outDir = join(here, 'www');

// Runtime assets only — not the docs (*.md) or backend SQL.
const ASSETS = ['index.html', 'sync.js'];

rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });

let copied = 0;
for (const name of ASSETS) {
  const from = join(srcDir, name);
  if (!existsSync(from)) {
    console.error(`✗ missing expected asset: ${from}`);
    process.exit(1);
  }
  copyFileSync(from, join(outDir, name));
  copied++;
}
console.log(`✓ copied ${copied} asset(s) into www/ (${ASSETS.join(', ')})`);
