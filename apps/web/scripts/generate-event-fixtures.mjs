// Contract fixtures are test-only. Nothing from here is imported by the application.
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { format, resolveConfig } from 'prettier';
const names = {
  ARTICLE_SEARCH_RESULTS: 'article-search-results',
  ARTICLE_DETAIL: 'article-detail',
  ARTICLE_COMPARISON: 'article-comparison',
  SIMILARITY_RESULTS: 'similarity-results',
  TECHNICAL_SHEET: 'technical-sheet',
  REQUEST_DRAFT: 'request-draft',
  SAVED_FILTER_LIST: 'saved-filter-list',
  SAVED_FILTER_CREATED: 'saved-filter-created',
  SAVED_FILTER_DELETED: 'saved-filter-deleted',
  ATTACHMENT_STATUS: 'attachment-status',
  ERROR: 'error-ui-event',
};
const events = [];
for (const [type, name] of Object.entries(names)) {
  const payload = JSON.parse(
    await readFile(
      new URL(`../../../docs/contracts/examples/${name}.json`, import.meta.url),
      'utf8',
    ),
  );
  events.push({
    id: type,
    messageId: 'fixture',
    type,
    schemaVersion: 1,
    sequence: 1,
    payload,
    createdAt: '2026-09-30T12:00:00Z',
  });
}
await mkdir(new URL('../src/app/testing', import.meta.url), { recursive: true });
await writeFile(
  new URL('../src/app/testing/events.generated.ts', import.meta.url),
  await format(
    `// Generated from public contract examples. Do not edit. Test-only.\nimport { UiEvent } from '../api/contracts';\nexport const events: UiEvent[] = ${JSON.stringify(events, null, 2)};\n`,
    {
      ...(await resolveConfig(
        new URL('../src/app/testing/events.generated.ts', import.meta.url).pathname,
      )),
      parser: 'typescript',
    },
  ),
);
