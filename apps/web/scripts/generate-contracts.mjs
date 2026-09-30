import { spawnSync } from 'node:child_process';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { format, resolveConfig } from 'prettier';
const input = fileURLToPath(
  new URL('../../../docs/contracts/application-api-v1.openapi.json', import.meta.url),
);
const output = fileURLToPath(
  new URL('../src/app/api/generated/application-api.ts', import.meta.url),
);
// Isolate generator's TS5 peer instead of overriding Angular's TS6 dependencies.
const result = spawnSync(
  'npx',
  [
    '--yes',
    '--package=openapi-typescript@7.13.0',
    '--package=typescript@5.9.3',
    'openapi-typescript',
    input,
    '-o',
    output,
  ],
  { stdio: 'inherit' },
);
if (result.status !== 0) process.exit(result.status ?? 1);
await writeFile(
  output,
  await format(await readFile(output, 'utf8'), {
    ...(await resolveConfig(output)),
    parser: 'typescript',
  }),
);
