import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router, UrlTree } from '@angular/router';
import { AuthService } from './auth.service';
import { API_BASE_URL } from '../api/config';
import { apiInterceptor } from '../api/interceptor';
import { authGuard, guestGuard } from './guards';
import { user } from '../../testing/fixtures';

describe('Cookie authentication', () => {
  let auth: AuthService;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([apiInterceptor])),
        provideHttpClientTesting(),
        { provide: API_BASE_URL, useValue: '/api/v1' },
      ],
    });
    auth = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  it('restores current user with credentials', async () => {
    const promise = auth.loadCurrentUser();
    const request = http.expectOne('/api/v1/auth/me');
    expect(request.request.withCredentials).toBe(true);
    request.flush(user);
    await promise;
    expect(auth.currentUser()).toEqual(user);
    expect(auth.authenticated()).toBe(true);
  });
  it('treats startup 401 as an ordinary guest, not an error loop', async () => {
    const promise = auth.loadCurrentUser();
    http.expectOne('/api/v1/auth/me').flush({}, { status: 401, statusText: 'Unauthorized' });
    await promise;
    expect(auth.status()).toBe('ready');
    expect(auth.connectionError()).toBeNull();
  });
  it('shows unavailable without trusting a cached user', async () => {
    const promise = auth.loadCurrentUser();
    http.expectOne('/api/v1/auth/me').error(new ProgressEvent('error'));
    await promise;
    expect(auth.status()).toBe('unavailable');
    expect(auth.authenticated()).toBe(false);
  });
  it('verifies login via auth/me rather than a local boolean', async () => {
    const promise = auth.login(user.email, 'fixture-only');
    http.expectOne('/api/v1/auth/login').flush(user);
    await Promise.resolve();
    http.expectOne('/api/v1/auth/me').flush(user);
    await promise;
    expect(auth.currentUser()).toEqual(user);
  });
  it('revokes the backend cookie and clears the user on logout', async () => {
    auth.currentUser.set(user);
    auth.status.set('ready');
    vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    const promise = auth.logout();
    http.expectOne('/api/v1/auth/logout').flush({ ok: true });
    await promise;
    expect(auth.currentUser()).toBeNull();
    TestBed.tick();
    expect(auth.sessionExpiredNotice()).toBeNull();
  });
  it('auth guard waits for auth/me and redirects a guest', async () => {
    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as never, {} as never),
    ) as Promise<boolean | UrlTree>;
    http.expectOne('/api/v1/auth/me').flush({}, { status: 401, statusText: 'Unauthorized' });
    expect((await result).toString()).toBe('/login');
  });
  it('failed logout clears local data but never claims remote revocation', async () => {
    auth.currentUser.set(user);
    auth.status.set('ready');
    vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    const promise = auth.logout();
    const rejected = expect(promise).rejects.toBeDefined();
    http.expectOne('/api/v1/auth/logout').error(new ProgressEvent('error'));
    await rejected;
    expect(auth.authenticated()).toBe(false);
    expect(auth.logoutNotice()).toContain('no pudimos confirmar');
  });
  it('auth guard accepts verified user', async () => {
    auth.currentUser.set(user);
    auth.status.set('ready');
    expect(await TestBed.runInInjectionContext(() => authGuard({} as never, {} as never))).toBe(
      true,
    );
  });
  it('guest guard redirects authenticated user', async () => {
    auth.currentUser.set(user);
    auth.status.set('ready');
    expect(
      (await TestBed.runInInjectionContext(() => guestGuard({} as never, {} as never))).toString(),
    ).toBe('/chat');
  });
  it('a protected 401 invalidates the session centrally', async () => {
    auth.currentUser.set(user);
    auth.status.set('ready');
    vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    TestBed.inject(importHttpClient())
      .get('/api/v1/conversations')
      .subscribe({ error: () => undefined });
    http.expectOne('/api/v1/conversations').flush({}, { status: 401, statusText: 'Unauthorized' });
    TestBed.tick();
    expect(auth.authenticated()).toBe(false);
    expect(auth.sessionExpiredNotice()).toContain('Tu sesión terminó');
  });
  it('403 does not clear a valid session', () => {
    auth.currentUser.set(user);
    auth.status.set('ready');
    TestBed.inject(importHttpClient())
      .get('/api/v1/conversations')
      .subscribe({ error: () => undefined });
    http.expectOne('/api/v1/conversations').flush({}, { status: 403, statusText: 'Forbidden' });
    TestBed.tick();
    expect(auth.authenticated()).toBe(true);
  });
});
import { HttpClient } from '@angular/common/http';
function importHttpClient(): typeof HttpClient {
  return HttpClient;
}
