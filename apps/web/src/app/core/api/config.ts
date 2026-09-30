import { InjectionToken } from '@angular/core';

/** Public deployment configuration only. Never put credentials here. */
export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL');
export interface PublicConfig {
  apiBaseUrl: string;
}
