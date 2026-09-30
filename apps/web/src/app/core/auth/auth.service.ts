import { HttpClient, HttpContext, HttpErrorResponse } from '@angular/common/http';
import { computed, effect, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { CurrentUser } from '../../api/contracts';
import { API_BASE_URL } from '../api/config';
import { safeError } from '../api/errors';
import { EXPECTED_UNAUTHENTICATED } from '../api/interceptor';
import { SessionEvents } from './session-events';
import {
  AUTH_STATUS,
  HTTP_STATUS,
  SESSION_REASON,
  type AuthStatus,
} from '../constants/ui.constants';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);
  private readonly router = inject(Router);
  private readonly sessions = inject(SessionEvents);
  private loading: Promise<void> | null = null;
  private generation = 0;
  readonly currentUser = signal<CurrentUser | null>(null);
  readonly authenticated = computed(() => this.currentUser() !== null);
  readonly status = signal<AuthStatus>(AUTH_STATUS.LOADING);
  readonly connectionError = signal<string | null>(null);
  readonly logoutNotice = signal<string | null>(null);
  readonly sessionExpiredNotice = signal<string | null>(null);

  constructor() {
    let revision = this.sessions.revision();
    effect(() => {
      const next = this.sessions.revision();
      if (next !== revision) {
        revision = next;
        this.sessionExpiredNotice.set(
          this.sessions.reason === SESSION_REASON.EXPIRED
            ? 'Tu sesión terminó. Iniciá sesión para continuar.'
            : null,
        );
        this.generation++;
        this.currentUser.set(null);
        this.status.set(AUTH_STATUS.READY);
        void this.router.navigateByUrl('/login', { replaceUrl: true });
      }
    });
  }

  ensureReady(): Promise<void> {
    if (this.status() === AUTH_STATUS.READY) return Promise.resolve();
    return this.loading ?? this.loadCurrentUser();
  }

  loadCurrentUser(): Promise<void> {
    if (this.loading) return this.loading;
    const generation = this.generation;
    this.status.set(AUTH_STATUS.LOADING);
    this.connectionError.set(null);
    this.loading = (async () => {
      try {
        const user = await firstValueFrom(
          this.http.get<CurrentUser>(`${this.base}/auth/me`, {
            context: new HttpContext().set(EXPECTED_UNAUTHENTICATED, true),
          }),
        );
        if (generation !== this.generation) return;
        this.currentUser.set(user);
        this.status.set(AUTH_STATUS.READY);
      } catch (error) {
        if (generation !== this.generation) return;
        this.currentUser.set(null);
        if (error instanceof HttpErrorResponse && error.status === HTTP_STATUS.UNAUTHORIZED)
          this.status.set(AUTH_STATUS.READY);
        else {
          this.status.set(AUTH_STATUS.UNAVAILABLE);
          this.connectionError.set(safeError(error));
        }
      } finally {
        this.loading = null;
      }
    })();
    return this.loading;
  }

  async login(email: string, password: string): Promise<void> {
    this.logoutNotice.set(null);
    this.sessionExpiredNotice.set(null);
    const generation = this.generation;
    await firstValueFrom(
      this.http.post<CurrentUser>(
        `${this.base}/auth/login`,
        { email, password },
        {
          context: new HttpContext().set(EXPECTED_UNAUTHENTICATED, true),
        },
      ),
    );
    if (generation !== this.generation) return;
    await this.loadCurrentUser();
    if (!this.authenticated()) throw new Error('Session verification failed');
  }

  async logout(): Promise<void> {
    // A failed logout cannot claim server revocation. The UI stays locked regardless.
    try {
      await firstValueFrom(this.http.post(`${this.base}/auth/logout`, {}));
      this.logoutNotice.set(null);
    } catch (error) {
      this.logoutNotice.set(
        'El espacio local se cerró, pero no pudimos confirmar la revocación de la sesión en el servidor. Volvé a intentar cerrar la sesión cuando se restablezca la conexión.',
      );
      throw error;
    } finally {
      this.generation++;
      this.currentUser.set(null);
      this.status.set('ready');
      this.sessions.invalidate(SESSION_REASON.LOGOUT);
      await this.router.navigateByUrl('/login', { replaceUrl: true });
    }
  }
}
