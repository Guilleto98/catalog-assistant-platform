import { Component, input, output, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SavedFilter } from '../../../api/contracts';
import { SavedFilterCommandMenu } from './saved-filter-command-menu';
import {
  CHAT_INPUT_POLICY,
  CHAT_MENU_POLICY,
  KEYBOARD_KEY,
  NAVIGATION_DELTA,
} from '../../../core/constants/ui.constants';

@Component({
  selector: 'app-chat-composer',
  imports: [FormsModule, SavedFilterCommandMenu],
  template: ` <div class="composer-wrap">
    @if (menuOpen()) {
      <app-saved-filter-command-menu
        [query]="filterQuery()"
        (selected)="selectFilter($event)"
        (closed)="closeMenu()"
      />
    }
    <form class="composer" (ngSubmit)="send()">
      <button
        type="button"
        class="attach-button"
        disabled
        title="Adjuntar archivo (próximamente)"
        aria-label="Adjuntar archivo (próximamente)"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          aria-hidden="true"
        >
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>
      <label class="sr-only" for="message">Escribí un mensaje</label>
      <textarea
        id="message"
        name="message"
        [(ngModel)]="text"
        placeholder="Escribí un mensaje…"
        rows="2"
        [maxlength]="inputPolicy.MAX_MESSAGE_LENGTH"
        [disabled]="disabled()"
        (input)="onInput()"
        (keydown)="keyDown($event)"
      ></textarea>
      <button
        type="button"
        class="filters-button"
        (click)="toggleMenu()"
        [disabled]="disabled()"
        aria-label="Filtros guardados"
        [attr.aria-expanded]="menuOpen()"
      >
        Filtros
      </button>
      <button
        class="send-button"
        type="submit"
        aria-label="Enviar mensaje"
        [disabled]="disabled() || !text.trim() || text === inputPolicy.FILTER_COMMAND_PREFIX"
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
          <path d="M12 19V5m-7 7 7-7 7 7" />
        </svg>
      </button>
    </form>
    <p class="composer-note">
      Enter para enviar · Shift + Enter para nueva línea · / para filtros. Contrastá las respuestas
      con el catálogo.
    </p>
  </div>`,
})
export class ChatComposer {
  readonly inputPolicy = CHAT_INPUT_POLICY;
  readonly disabled = input(false);
  readonly clearOnSubmit = input(true);
  readonly submitted = output<string>();
  readonly menuOpen = signal(false);
  readonly filterQuery = signal('');
  private readonly menu = viewChild(SavedFilterCommandMenu);
  text = '';
  clear(): void {
    this.text = '';
    this.closeMenu();
  }
  send(): void {
    if (
      this.disabled() ||
      !this.text.trim() ||
      this.text === CHAT_INPUT_POLICY.FILTER_COMMAND_PREFIX
    )
      return;
    this.submitted.emit(this.text);
    if (this.clearOnSubmit()) this.clear();
  }
  onInput(): void {
    if (this.text.startsWith(CHAT_INPUT_POLICY.FILTER_COMMAND_PREFIX)) {
      this.filterQuery.set(this.text.slice(CHAT_INPUT_POLICY.FILTER_COMMAND_PREFIX.length));
      this.menu()?.active.set(0);
      this.openMenu();
    } else if (this.menuOpen()) this.closeMenu();
  }
  openMenu(): void {
    if (this.disabled() || this.menuOpen()) return;
    this.menuOpen.set(true);
    setTimeout(() => void this.menu()?.load(), CHAT_MENU_POLICY.OPEN_DELAY_MS);
  }
  closeMenu(): void {
    this.menuOpen.set(false);
    if (this.text.startsWith(CHAT_INPUT_POLICY.FILTER_COMMAND_PREFIX)) this.text = '';
    this.filterQuery.set('');
  }
  toggleMenu(): void {
    if (this.menuOpen()) this.closeMenu();
    else this.openMenu();
  }
  selectFilter(filter: SavedFilter): void {
    this.text = `Ejecutá el filtro guardado "${filter.name}" con ID exacto ${filter.id}.`;
    this.menuOpen.set(false);
    this.send();
  }
  keyDown(event: KeyboardEvent): void {
    if (this.menuOpen()) {
      if (event.key === KEYBOARD_KEY.ARROW_DOWN || event.key === KEYBOARD_KEY.ARROW_UP) {
        event.preventDefault();
        this.menu()?.move(
          event.key === KEYBOARD_KEY.ARROW_DOWN ? NAVIGATION_DELTA.NEXT : NAVIGATION_DELTA.PREVIOUS,
        );
        return;
      }
      if (event.key === KEYBOARD_KEY.ESCAPE) {
        event.preventDefault();
        this.closeMenu();
        return;
      }
      if (event.key === KEYBOARD_KEY.ENTER && !event.shiftKey) {
        event.preventDefault();
        this.menu()?.choose();
        return;
      }
    }
    if (event.key === KEYBOARD_KEY.ENTER && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      this.send();
    }
  }
}
