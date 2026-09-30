import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { API_BASE_URL, PublicConfig } from './app/core/api/config';

async function start(): Promise<void> {
  const response = await fetch('/config.json', { cache: 'no-store' });
  if (!response.ok) throw new Error('Missing public configuration');
  const config: PublicConfig = await response.json();
  if (typeof config.apiBaseUrl !== 'string') throw new Error('Invalid public configuration');
  const url = new URL(config.apiBaseUrl, location.origin);
  if (
    !['http:', 'https:'].includes(url.protocol) ||
    url.username ||
    url.password ||
    !url.pathname.endsWith('/api/v1')
  )
    throw new Error('Invalid Application API URL');
  await bootstrapApplication(App, {
    providers: [
      ...appConfig.providers,
      { provide: API_BASE_URL, useValue: config.apiBaseUrl.replace(/\/$/, '') },
    ],
  });
}
void start().catch(() => {
  const message = document.createElement('p');
  message.textContent =
    'No se pudo iniciar la aplicación. Verificá la configuración o recargá la página.';
  document.body.replaceChildren(message);
});
