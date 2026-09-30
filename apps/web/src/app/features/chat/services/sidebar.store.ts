import { effect, inject, Injectable, signal } from '@angular/core';
import { Conversation } from '../../../api/contracts';
import { AuthService } from '../../../core/auth/auth.service';
import { safeError } from '../../../core/api/errors';
import { ConversationsService } from './conversations.service';
import { CHAT_PAGINATION } from '../../../core/constants/ui.constants';

@Injectable({ providedIn: 'root' })
export class SidebarStore {
  private readonly api = inject(ConversationsService);
  private readonly auth = inject(AuthService);
  private generation = 0;
  readonly conversations = signal<Conversation[]>([]);
  readonly loading = signal(false);
  readonly creating = signal(false);
  readonly error = signal<string | null>(null);
  readonly hasMore = signal(false);
  private page: number = CHAT_PAGINATION.INITIAL_PAGE_CURSOR;
  constructor() {
    effect(() => {
      if (!this.auth.authenticated()) this.clear();
    });
  }
  clear(): void {
    this.generation++;
    this.conversations.set([]);
    this.error.set(null);
    this.loading.set(false);
    this.creating.set(false);
    this.hasMore.set(false);
    this.page = CHAT_PAGINATION.INITIAL_PAGE_CURSOR;
  }
  async load(more = false): Promise<void> {
    if (!this.auth.authenticated() || (more && this.loading())) return;
    const generation = ++this.generation;
    const page = more ? this.page + CHAT_PAGINATION.PAGE_INDEX_ORIGIN : CHAT_PAGINATION.FIRST_PAGE;
    this.loading.set(true);
    this.error.set(null);
    try {
      const result = await this.api.listConversations(page);
      if (generation !== this.generation || !this.auth.authenticated()) return;
      this.page = page;
      this.conversations.set(more ? [...this.conversations(), ...result.items] : result.items);
      this.hasMore.set(page * result.pageSize < result.total);
    } catch (error) {
      if (generation === this.generation) this.error.set(safeError(error));
    } finally {
      if (generation === this.generation) this.loading.set(false);
    }
  }
  async create(): Promise<Conversation | null> {
    if (this.creating() || !this.auth.authenticated()) return null;
    const generation = this.generation;
    this.creating.set(true);
    this.error.set(null);
    try {
      const conversation = await this.api.createConversation();
      if (generation !== this.generation || !this.auth.authenticated()) return null;
      await this.load();
      return this.auth.authenticated() ? conversation : null;
    } catch (error) {
      if (generation === this.generation) this.error.set(safeError(error));
      return null;
    } finally {
      this.creating.set(false);
    }
  }
}
