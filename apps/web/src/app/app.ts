import { Component, inject } from '@angular/core';
import { AuthService } from './core/auth/auth.service';
import { RouterOutlet } from '@angular/router';
import { AUTH_STATUS } from './core/constants/ui.constants';

@Component({
  imports: [RouterOutlet],
  selector: 'app-root',
  styleUrl: './app.scss',
  template: `@if (auth.status() === authStatus.LOADING) {
      <main class="session-screen" role="status">
        <img class="brand-mark" src="/brand/agrolink-symbol-smooth-3d.svg" alt="" />
        <p>Restaurando tu sesión…</p>
      </main>
    } @else if (auth.status() === authStatus.UNAVAILABLE) {
      <main class="session-screen">
        <h1>No pudimos conectar</h1>
        <p role="alert">{{ auth.connectionError() }}</p>
        <button class="primary" (click)="retry()">Volver a intentar</button>
      </main>
    } @else {
      <router-outlet />
    }`,
})
export class App {
  readonly auth = inject(AuthService);
  readonly authStatus = AUTH_STATUS;
  async retry(): Promise<void> {
    await this.auth.loadCurrentUser();
    if (this.auth.status() === AUTH_STATUS.READY) location.reload();
  }
}
