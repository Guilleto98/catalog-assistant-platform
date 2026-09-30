import { DatePipe } from '@angular/common';
import { Component, inject, input, output, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../../core/auth/auth.service';
import { SidebarStore } from '../services/sidebar.store';
import { safeError } from '../../../core/api/errors';
import { ACCOUNT_ROLE } from '../../../core/constants/ui.constants';

@Component({
  selector: 'app-chat-sidebar',
  imports: [RouterLink, DatePipe],
  template: ` <aside class="sidebar">
    <button
      type="button"
      class="collapse-sidebar"
      [attr.aria-label]="collapsed() ? 'Expandir panel' : 'Colapsar panel'"
      [title]="collapsed() ? 'Expandir panel' : 'Colapsar panel'"
      (click)="collapse.emit()"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="m15 18-6-6 6-6" />
      </svg>
    </button>
    <a class="brand" routerLink="/chat"
      ><span class="brand-icon"><img src="/brand/agrolink-symbol-smooth-3d.svg" alt="" /></span
      ><span>Catálogo<span class="brand-subtitle">Asistente de artículos</span></span></a
    >
    <button
      class="new-conversation"
      aria-label="Nueva conversación"
      (click)="newConversation.emit()"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        aria-hidden="true"
      >
        <path d="M12 5v14M5 12h14" /></svg
      ><span class="sidebar-text">Nueva conversación</span>
    </button>
    <p class="sidebar-label">CONVERSACIONES</p>
    <nav aria-label="Conversaciones" class="conversation-list">
      @for (conversation of sidebar.conversations(); track conversation.id) {
        <a
          [routerLink]="['/chat', conversation.id]"
          (click)="selected.emit()"
          [class.active]="conversation.id === activeId()"
          [attr.aria-current]="conversation.id === activeId() ? 'page' : null"
        >
          <strong>{{ conversation.title }}</strong
          ><span>{{ conversation.preview || 'Sin mensajes todavía' }}</span>
          <time>{{ conversation.lastMessageAt || conversation.createdAt | date: 'd MMM' }}</time>
        </a>
      } @empty {
        @if (!sidebar.loading() && !sidebar.error()) {
          <p class="muted sidebar-empty">Todavía no hay conversaciones.</p>
        }
      }
      @if (sidebar.loading()) {
        <p role="status" class="sidebar-empty">Cargando conversaciones…</p>
      }
      @if (sidebar.error()) {
        <p class="error" role="alert">{{ sidebar.error() }}</p>
        <button (click)="sidebar.load()">Volver a intentar</button>
      }
      @if (sidebar.hasMore()) {
        <button (click)="sidebar.load(true)" [disabled]="sidebar.loading()">
          Ver más conversaciones
        </button>
      }
    </nav>
    <footer class="profile">
      @if (auth.currentUser(); as user) {
        <strong>{{ user.organization?.name || 'Espacio de trabajo' }}</strong
        ><span>{{ user.email }}</span>
        @if (user.role === accountRole.INTERNAL_ADMIN) {
          <small>Administrador interno</small>
        }
      }
      <button (click)="logout()" [disabled]="loggingOut()">
        {{ loggingOut() ? 'Cerrando…' : 'Cerrar sesión' }}
      </button>
      @if (logoutError()) {
        <p class="error" role="alert">{{ logoutError() }}</p>
      }
    </footer>
  </aside>`,
})
export class ChatSidebar {
  readonly accountRole = ACCOUNT_ROLE;
  readonly auth = inject(AuthService);
  readonly sidebar = inject(SidebarStore);
  readonly activeId = input<string | null>(null);
  readonly collapsed = input(false);
  readonly collapse = output<void>();
  readonly newConversation = output<void>();
  readonly selected = output<void>();
  readonly loggingOut = signal(false);
  readonly logoutError = signal<string | null>(null);
  async logout(): Promise<void> {
    if (this.loggingOut()) return;
    this.loggingOut.set(true);
    try {
      await this.auth.logout();
    } catch (error) {
      this.logoutError.set(safeError(error));
    } finally {
      this.loggingOut.set(false);
    }
  }
}
