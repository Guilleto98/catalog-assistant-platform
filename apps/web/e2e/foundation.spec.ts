import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const root = process.env['WEB_SMOKE_ROOT'];
const password = process.env['WEB_SMOKE_PASSWORD'];
const python = process.env['WEB_SMOKE_PYTHON'];
const api = 'http://localhost:3101/api/v1';
const output = resolve('../../output/playwright');
const report: Record<string, boolean | string | number> = {};
function database(
  action: 'counts' | 'conversations' | 'expire' | 'isolation' | 'tools',
  cid = '',
): string {
  if (!root || !python) throw new Error('Use npm run web:smoke for an isolated backend');
  const code = `import sqlite3,sys,json\ndb=sqlite3.connect(sys.argv[1]+'/application.db')\naction=sys.argv[2]\nif action=='counts':\n print(json.dumps([db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('agent_runs','tool_executions','ui_events')]))\nelif action=='conversations':\n print(db.execute('SELECT count(*) FROM conversations').fetchone()[0])\nelif action=='tools':\n print(json.dumps(db.execute('SELECT tool_name,status,error_code FROM tool_executions WHERE agent_run_id=? ORDER BY sequence',(sys.argv[3],)).fetchall()))\nelif action=='expire':\n db.execute("UPDATE auth_sessions SET expires_at='2000-01-01 00:00:00'");db.commit()\nelse:\n rows=db.execute('SELECT arguments_json FROM tool_executions t JOIN agent_runs r ON r.id=t.agent_run_id WHERE r.conversation_id=?',(sys.argv[3],)).fetchall()\n print(json.dumps([json.loads(r[0]) for r in rows]))`;
  return execFileSync(python, ['-c', code, root, action, cid], { encoding: 'utf8' }).trim();
}

test('real cookie login → agent → UiEvents → refresh → isolation → logout and expiry', async ({
  page,
  context,
}) => {
  test.skip(!root || !password, 'Run through npm run web:smoke');
  mkdirSync(output, { recursive: true });
  const requests: string[] = [];
  page.on('request', (request) => {
    if (['xhr', 'fetch'].includes(request.resourceType())) requests.push(request.url());
  });
  const crashes: string[] = [];
  page.on('pageerror', (error) => crashes.push(error.name));
  // Deployment config only: all business requests go to the real isolated API.
  await page.route('**/config.json', (route) =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify({ apiBaseUrl: api }) }),
  );
  await page.goto('/chat');
  await expect(page).toHaveURL(/\/login$/);
  await page.screenshot({ path: resolve(output, '6d-login.png') });
  async function login() {
    await page.getByLabel('Correo electrónico').fill('web-smoke@example.test');
    await page.getByLabel('Contraseña', { exact: true }).fill(password!);
    await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
    await expect(page).toHaveURL(/\/chat$/);
    await expect(page.getByRole('navigation', { name: 'Conversaciones' })).toBeVisible();
  }
  await login();
  report['login'] = true;
  const cookies = await context.cookies();
  const cookie = cookies.find((item) => item.name === 'solvo_session');
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.sameSite).toBe('Lax');
  report['httpOnlyCookie'] = true;
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
  expect(await page.evaluate(() => document.cookie)).not.toContain('solvo_session');
  report['noBrowserTokens'] = true;
  await expect(page).toHaveURL(/\/chat$/);
  await expect(page.getByLabel('Escribí un mensaje', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Colapsar panel' }).click();
  await expect(page.locator('.chat-shell')).toHaveClass(/sidebar-collapsed/);
  await expect(page.getByRole('button', { name: 'Nueva conversación', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Expandir panel' }).click();
  expect(database('conversations')).toBe('0');
  for (let i = 0; i < 3; i++)
    await page.getByRole('button', { name: 'Nueva conversación', exact: true }).click();
  expect(database('conversations')).toBe('0');
  await page.screenshot({ path: resolve(output, '6d-chat-empty.png') });
  report['emptyComposer'] = true;
  await page.getByRole('button', { name: 'Filtros guardados' }).click();
  await expect(page.locator('.filter-menu')).toBeVisible();
  await expect(page.locator('.filter-menu')).toContainText('Todavía no tenés filtros guardados');
  await page.screenshot({ path: resolve(output, '6d-filters-empty.png') });
  await page.getByRole('button', { name: 'Cerrar filtros' }).click();
  await page.getByLabel('Escribí un mensaje', { exact: true }).fill('/');
  await expect(page.locator('.filter-menu')).toBeVisible();
  await page.getByLabel('Escribí un mensaje', { exact: true }).press('Escape');
  await expect(page.locator('.filter-menu')).not.toBeVisible();
  report['filterEntryPoints'] = true;
  async function send(text: string, eventSelector?: string) {
    const responsePromise = page.waitForResponse(
      (response) => response.url().endsWith('/messages') && response.request().method() === 'POST',
      { timeout: 180000 },
    );
    await page.getByLabel('Escribí un mensaje', { exact: true }).fill(text);
    await page.getByRole('button', { name: 'Enviar mensaje' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Pensando' })).toBeVisible();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.run.status).toBe('COMPLETED');
    await expect(page.getByLabel('Escribí un mensaje', { exact: true })).toBeEnabled({
      timeout: 10000,
    });
    if (eventSelector) await expect(page.locator(eventSelector).last()).toBeVisible();
    await expect
      .poll(() =>
        page
          .locator('.message-area')
          .evaluate((element) => element.scrollHeight - element.scrollTop - element.clientHeight),
      )
      .toBeLessThan(50);
    console.info('Smoke: turno y evento verificados');
    return body;
  }
  await send('Buscame bife ancho para China.', 'app-article-search-results');
  await expect(page).toHaveURL(/\/chat\/[0-9a-f-]+$/);
  expect(database('conversations')).toBe('1');
  expect(JSON.parse(database('counts'))[0]).toBe(1);
  const conversationUrl = page.url();
  report['lazyConversation'] = true;
  report['search'] = true;
  await page.screenshot({ path: resolve(output, '6d-chat-search.png') });
  await send('Mostrame el primero.', 'app-article-detail');
  report['contextDetail'] = true;
  await page.locator('app-article-detail').scrollIntoViewIfNeeded();
  await page.screenshot({ path: resolve(output, '6d-chat-detail.png') });
  await send('Guardá esta búsqueda como "China congelados smoke".', 'app-saved-filter-created');
  await page.getByRole('button', { name: 'Filtros guardados' }).click();
  await expect(page.locator('.filter-menu')).toContainText('China congelados smoke');
  await page.screenshot({ path: resolve(output, '6d-filters-palette.png') });
  const filterResponse = page.waitForResponse(
    (response) => response.url().endsWith('/messages') && response.request().method() === 'POST',
    { timeout: 180000 },
  );
  await page.getByRole('option', { name: /China congelados smoke/ }).click();
  expect((await filterResponse).status()).toBe(200);
  await expect(page.locator('app-article-search-results').last()).toBeVisible();
  report['savedFilterExecution'] = true;
  await page.getByLabel('Escribí un mensaje', { exact: true }).fill('/china');
  await expect(page.locator('.filter-menu')).toContainText('China congelados smoke');
  await page.getByLabel('Escribí un mensaje', { exact: true }).press('Escape');
  report['savedFilterSlash'] = true;
  await send('Buscame bife ancho para China y Brasil.', 'app-article-search-results');
  await send('Compará el primero y el segundo.', 'app-article-comparison');
  report['comparison'] = true;
  const similar = await send(
    'Buscame algo parecido al 900001, pero China es obligatorio.',
    'app-similarity-results',
  );
  report['similarityEventTypes'] = similar.assistantMessage.uiEvents
    .map((e: { type: string }) => e.type)
    .join(',');
  report['similarityToolStatuses'] = database('tools', similar.run.id);
  const payload = similar.assistantMessage.uiEvents.find(
    (e: { type: string }) => e.type === 'SIMILARITY_RESULTS',
  ).payload;
  expect(
    payload.eligibleCandidates.find(
      (c: { article: { code: string } }) => c.article.code === '900006',
    ).eligibility,
  ).toBe('ELIGIBLE');
  expect(
    payload.ineligibleCandidates.find(
      (c: { article: { code: string } }) => c.article.code === '900004',
    ).eligibility,
  ).toBe('INELIGIBLE');
  await expect(page.locator('.eligible')).toContainText('900006');
  await expect(page.locator('.eligible')).not.toContainText('900004');
  await expect(page.locator('.ineligible')).toContainText('900004');
  report['similaritySeparated'] = true;
  await page.locator('app-similarity-results h3').scrollIntoViewIfNeeded();
  await expect(page.locator('app-similarity-results h3')).toBeInViewport();
  await page.screenshot({ path: resolve(output, '6d-similarity.png') });
  const scope = await send('Ayudame a preparar una clase de Ciencias Sociales.');
  expect(scope.assistantMessage.uiEvents).toHaveLength(0);
  report['outOfDomain'] = true;
  const countBefore = database('counts');
  const messageCount = await page.locator('app-message-bubble').count();
  await page.reload();
  await expect(page).toHaveURL(conversationUrl);
  await expect(page.locator('app-message-bubble')).toHaveCount(messageCount);
  await expect
    .poll(() =>
      page
        .locator('.message-area')
        .evaluate((element) => element.scrollHeight - element.scrollTop - element.clientHeight),
    )
    .toBeLessThan(50);
  await expect(page.locator('app-article-detail')).toBeVisible();
  expect(database('counts')).toBe(countBefore);
  report['refreshWithoutAgentExecution'] = true;
  await page.goto(conversationUrl);
  await expect(page.locator('app-message-bubble')).toHaveCount(messageCount);
  report['directUrl'] = true;
  await page.getByRole('button', { name: 'Nueva conversación', exact: true }).click();
  await expect(page).toHaveURL(/\/chat$/);
  await send('Solo los de China.');
  const b = page.url().split('/').at(-1)!;
  expect(b).not.toBe(conversationUrl.split('/').at(-1));
  expect(database('isolation', b)).not.toContain('BIFE_ANCHO');
  report['conversationIsolation'] = true;
  await page.goto('/chat/00000000-0000-0000-0000-000000000000');
  await expect(page.getByRole('heading', { name: 'Conversación no encontrada.' })).toBeVisible();
  report['notFound'] = true;
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(conversationUrl);
  await expect(page.locator('app-message-bubble')).toHaveCount(messageCount);
  await page.getByRole('button', { name: 'Abrir conversaciones' }).click();
  await expect(page.getByRole('navigation', { name: 'Conversaciones' })).toBeVisible();
  await page.getByRole('button', { name: 'Cerrar menú' }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: resolve(output, '6d-mobile.png') });
  report['mobileNoOverflow'] = true;
  await page.setViewportSize({ width: 1440, height: 960 });
  await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect((await context.cookies()).some((c) => c.name === 'solvo_session')).toBe(false);
  await page.goBack();
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.locator('app-message-bubble').count()).toBe(0);
  report['logoutAndBack'] = true;
  await login();
  database('expire');
  await page.reload();
  await expect(page).toHaveURL(/\/login$/);
  report['sessionExpiry'] = true;
  await page.route('http://localhost:3101/**', (route) => route.abort('connectionrefused'));
  await page.reload();
  await expect(page.getByRole('heading', { name: 'No pudimos conectar' })).toBeVisible();
  report['backendUnavailable'] = true;
  await page.unroute('http://localhost:3101/**');
  await page.getByRole('button', { name: 'Volver a intentar', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByLabel('Correo electrónico')).toBeVisible();
  report['connectionRecovery'] = true;
  expect(crashes).toEqual([]);
  expect(requests.some((url) => /:3000|openai\.com|:8000/.test(url))).toBe(false);
  report['noDirectProviderCatalogAdk'] = true;
  report['pageErrors'] = crashes.length;
  writeFileSync(resolve(output, '6d-smoke-result.json'), JSON.stringify(report, null, 2));
});
