import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { HTTP_STATUS } from '../../core/constants/ui.constants';
import { safeError } from '../../core/api/errors';
import { HttpErrorResponse } from '@angular/common/http';

@Component({
  selector: 'app-login',
  imports: [FormsModule],
  template: ` <main class="login-page">
    <section class="login-story" aria-label="Asistente de artículos">
      <a class="brand" href="/"
        ><img class="brand-logo" src="/brand/agrolink-symbol-smooth-3d.svg" alt="" /><span
          >Catálogo · Asistente</span
        ></a
      >
      <div>
        <p class="eyebrow">UN ESPACIO PARA CONSULTAR</p>
        <h1>La información que necesitás,<br />en una conversación.</h1>
        <p>
          Buscá artículos, consultá sus características y compará alternativas con información del
          catálogo.
        </p>
      </div>
      <p class="story-footer">Tu espacio de trabajo, con conversaciones guardadas.</p>
    </section>
    <section class="login-panel">
      <form (ngSubmit)="submit()" #form="ngForm" class="login-form">
        @if (auth.logoutNotice()) {
          <p class="error" role="alert">{{ auth.logoutNotice() }}</p>
          <button type="button" (click)="retryLogout()" [disabled]="busy()">
            Confirmar cierre de sesión
          </button>
        }
        @if (auth.sessionExpiredNotice()) {
          <p class="session-notice" role="status">{{ auth.sessionExpiredNotice() }}</p>
        }
        <p class="eyebrow">BIENVENIDO</p>
        <h2>Iniciar sesión</h2>
        <p class="muted">Ingresá con tu cuenta para continuar.</p>
        <label for="email">Correo electrónico</label>
        <input
          id="email"
          name="email"
          type="email"
          [(ngModel)]="email"
          required
          email
          autocomplete="username"
          [disabled]="busy()"
        />
        <label for="password">Contraseña</label>
        <input
          id="password"
          name="password"
          type="password"
          [(ngModel)]="password"
          required
          autocomplete="current-password"
          [disabled]="busy()"
        />
        @if (error()) {
          <p class="error" role="alert">{{ error() }}</p>
        }
        @if (auth.connectionError()) {
          <p class="error" role="alert">{{ auth.connectionError() }}</p>
        }
        <button class="primary" type="submit" [disabled]="busy() || form.invalid">
          {{ busy() ? 'Ingresando…' : 'Iniciar sesión' }}
        </button>
        <p class="login-note">Acceso seguro a tu espacio de consultas.</p>
      </form>
    </section>
  </main>`,
})
export class LoginPage {
  readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  email = '';
  password = '';
  readonly busy = signal(false);
  readonly error = signal<string | null>(null);

  async submit(): Promise<void> {
    if (this.busy() || !this.email.trim() || !this.password) return;
    this.busy.set(true);
    this.error.set(null);
    try {
      await this.auth.login(this.email.trim(), this.password);
      if (this.auth.authenticated()) await this.router.navigateByUrl('/chat');
    } catch (error) {
      this.error.set(
        error instanceof HttpErrorResponse && error.status === HTTP_STATUS.UNAUTHORIZED
          ? 'El correo o la contraseña no son correctos.'
          : safeError(error),
      );
    } finally {
      this.password = '';
      this.busy.set(false);
    }
  }
  async retryLogout(): Promise<void> {
    this.busy.set(true);
    try {
      await this.auth.logout();
    } catch {
      /* AuthService retains the safe warning. */
    } finally {
      this.busy.set(false);
    }
  }
}
