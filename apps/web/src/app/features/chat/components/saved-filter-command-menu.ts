import { Component, computed, inject, input, output, signal } from '@angular/core';
import { SavedFilter } from '../../../api/contracts';
import { safeError } from '../../../core/api/errors';
import { ConversationsService } from '../services/conversations.service';

@Component({
  selector: 'app-saved-filter-command-menu',
  template: ` <section class="filter-menu" aria-label="Filtros guardados">
    <header>
      <strong>Filtros guardados</strong
      ><button type="button" aria-label="Cerrar filtros" (click)="closed.emit()">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          aria-hidden="true"
        >
          <path d="M5 5l14 14M19 5 5 19" />
        </svg>
      </button>
    </header>
    @if (loading()) {
      <p role="status">Cargando filtros…</p>
    } @else if (error()) {
      <p role="alert">{{ error() }}</p>
      <button type="button" (click)="load()">Reintentar</button>
    } @else {
      <div role="listbox" aria-label="Elegir filtro guardado">
        @for (filter of visible(); track filter.id; let index = $index) {
          <button
            type="button"
            role="option"
            [attr.aria-selected]="index === active()"
            [class.active]="index === active()"
            (mouseenter)="active.set(index)"
            (click)="selected.emit(filter)"
          >
            <strong>{{ filter.name }}</strong
            ><small>{{ filter.criteria.filters.length }} criterios</small>
          </button>
        } @empty {
          <p>
            {{
              filters().length
                ? 'No hay filtros que coincidan.'
                : 'Todavía no tenés filtros guardados. Podés guardar una búsqueda desde el chat.'
            }}
          </p>
        }
      </div>
    }
  </section>`,
})
export class SavedFilterCommandMenu {
  private readonly api = inject(ConversationsService);
  readonly query = input('');
  readonly selected = output<SavedFilter>();
  readonly closed = output<void>();
  readonly filters = signal<SavedFilter[]>([]);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly active = signal(0);
  readonly visible = computed(() => {
    const term = this.query().trim().toLocaleLowerCase();
    return this.filters().filter((filter) => filter.name.toLocaleLowerCase().includes(term));
  });
  async load(): Promise<void> {
    if (this.loading()) return;
    this.loading.set(true);
    this.error.set(null);
    try {
      this.filters.set((await this.api.listSavedFilters()).filters);
      this.active.set(0);
    } catch (error) {
      this.error.set(safeError(error));
    } finally {
      this.loading.set(false);
    }
  }
  move(delta: number): void {
    if (this.visible().length)
      this.active.set((this.active() + delta + this.visible().length) % this.visible().length);
  }
  choose(): void {
    const filter = this.visible()[this.active()];
    if (filter) this.selected.emit(filter);
  }
}
