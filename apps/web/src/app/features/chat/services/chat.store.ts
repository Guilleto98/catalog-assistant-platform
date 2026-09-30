import { effect, inject, Injectable, signal } from '@angular/core';
import { Conversation, Message, SendRequest, SendResponse } from '../../../api/contracts';
import { AuthService } from '../../../core/auth/auth.service';
import { safeError } from '../../../core/api/errors';
import { ConversationsService } from './conversations.service';
import { SidebarStore } from './sidebar.store';
import {
  AGENT_RUN_STATUS,
  CHAT_INPUT_POLICY,
  CHAT_PAGINATION,
  CONVERSATION_STATUS,
  MESSAGE_ROLE,
  STATE_POLICY,
} from '../../../core/constants/ui.constants';

interface PendingSend {
  conversationId: string;
  request: SendRequest;
  persistedId: string | null;
}
@Injectable({ providedIn: 'root' })
export class ChatStore {
  private readonly api = inject(ConversationsService);
  private readonly sidebar = inject(SidebarStore);
  private readonly auth = inject(AuthService);
  private generation = 0;
  private readonly pendingByConversation = new Map<string, PendingSend>();
  private readonly firstMessages = new Map<string, string>();
  readonly active = signal<Conversation | null>(null);
  readonly messages = signal<Message[]>([]);
  readonly loading = signal(false);
  readonly sending = signal(false);
  readonly loadError = signal<string | null>(null);
  readonly sendError = signal<string | null>(null);
  readonly pending = signal<PendingSend | null>(null);
  readonly scrollRevision = signal(0);
  constructor() {
    effect(() => {
      if (!this.auth.authenticated()) this.clear(true);
    });
  }
  clear(session = false): void {
    this.generation++;
    this.active.set(null);
    this.messages.set([]);
    this.loading.set(false);
    this.sending.set(false);
    this.loadError.set(null);
    this.sendError.set(null);
    this.pending.set(null);
    if (session) {
      this.pendingByConversation.clear();
      this.firstMessages.clear();
    }
  }
  queueFirstMessage(id: string, text: string): void {
    this.firstMessages.set(id, text);
  }
  takeFirstMessage(id: string): string | null {
    const text = this.firstMessages.get(id) ?? null;
    this.firstMessages.delete(id);
    return text;
  }
  private async history(id: string): Promise<Message[]> {
    const messages: Message[] = [];
    for (let page = CHAT_PAGINATION.FIRST_PAGE; ; page++) {
      const result = await this.api.getMessages(id, page);
      messages.push(...result.items);
      const loadedThrough = page * result.pageSize;
      if (loadedThrough >= result.total || result.items.length === 0) return messages;
    }
  }
  async open(id: string | null): Promise<void> {
    this.clear();
    if (!id || !this.auth.authenticated()) return;
    const generation = this.generation;
    this.loading.set(true);
    try {
      const [conversation, messages] = await Promise.all([
        this.api.getConversation(id),
        this.history(id),
      ]);
      if (generation !== this.generation || !this.auth.authenticated()) return;
      this.active.set(conversation);
      this.messages.set(messages);
      const pending = this.pendingByConversation.get(id) ?? null;
      this.pending.set(pending);
      if (pending)
        this.sendError.set(
          'Este envío todavía necesita confirmación. Podés consultar su resultado sin duplicarlo.',
        );
      this.scrollRevision.update((value) => value + STATE_POLICY.REVISION_INCREMENT);
    } catch (error) {
      if (generation === this.generation) this.loadError.set(safeError(error));
    } finally {
      if (generation === this.generation) this.loading.set(false);
    }
  }
  async send(text: string): Promise<void> {
    const conversation = this.active();
    if (
      !conversation ||
      conversation.status !== CONVERSATION_STATUS.ACTIVE ||
      this.sending() ||
      this.pending() ||
      !text.trim() ||
      text.length > CHAT_INPUT_POLICY.MAX_MESSAGE_LENGTH
    )
      return;
    const pending: PendingSend = {
      conversationId: conversation.id,
      request: { clientMessageId: crypto.randomUUID(), text: text.trim(), attachmentIds: [] },
      persistedId: null,
    };
    this.pendingByConversation.set(conversation.id, pending);
    this.pending.set(pending);
    await this.perform(pending);
  }
  async retry(): Promise<void> {
    const pending = this.pending();
    if (pending && !this.sending()) await this.perform(pending);
  }
  async dismissPending(): Promise<void> {
    const pending = this.pending();
    if (!pending || this.sending()) return;
    this.pendingByConversation.delete(pending.conversationId);
    this.pending.set(null);
    await this.open(pending.conversationId);
  }
  private merge(messages: Message[]): void {
    const existing = [...this.messages()];
    for (const message of messages) {
      const index = existing.findIndex((item) => item.id === message.id);
      if (index < 0) existing.push(message);
      else existing[index] = message;
    }
    this.messages.set(existing);
  }
  private async perform(pending: PendingSend): Promise<void> {
    const generation = this.generation;
    const userId = this.auth.currentUser()?.id;
    this.sending.set(true);
    this.sendError.set(null);
    try {
      const result = await this.api.sendMessage(pending.conversationId, pending.request);
      if (!this.isCurrentSend(generation, userId)) return;
      this.applySendResponse(pending, result);
      await this.refreshActiveConversation(pending.conversationId, generation);
    } catch (error) {
      await this.recoverFailedSend(pending, error, generation, userId);
    } finally {
      if (generation === this.generation) this.sending.set(false);
    }
  }

  private isCurrentSend(generation: number, userId: string | undefined): boolean {
    return generation === this.generation && userId === this.auth.currentUser()?.id;
  }

  private applySendResponse(pending: PendingSend, result: SendResponse): void {
    pending.persistedId = result.userMessage.id;
    this.merge([result.userMessage, ...(result.assistantMessage ? [result.assistantMessage] : [])]);
    if (result.run.status === AGENT_RUN_STATUS.COMPLETED) {
      this.pendingByConversation.delete(pending.conversationId);
      this.pending.set(null);
    } else {
      this.pending.set({ ...pending });
      this.sendError.set(this.messageForIncompleteRun(result.run.status));
    }
    this.scrollRevision.update((value) => value + CHAT_PAGINATION.PAGE_INDEX_ORIGIN);
  }

  private messageForIncompleteRun(status: SendResponse['run']['status']): string {
    return status === AGENT_RUN_STATUS.STARTED
      ? 'La consulta sigue en proceso. Consultá nuevamente su resultado.'
      : 'La consulta quedó registrada, pero no pudo completarse. No se ejecutará otra vez al consultar el resultado. Para intentarlo de nuevo, liberá el envío y enviá una nueva consulta.';
  }

  private async refreshActiveConversation(id: string, generation: number): Promise<void> {
    await this.sidebar.load();
    const updated = this.sidebar.conversations().find((item) => item.id === id);
    if (updated && generation === this.generation) this.active.set(updated);
  }

  private async recoverFailedSend(
    pending: PendingSend,
    error: unknown,
    generation: number,
    userId: string | undefined,
  ): Promise<void> {
    if (!this.isCurrentSend(generation, userId)) return;
    this.sendError.set(safeError(error));
    try {
      const history = await this.history(pending.conversationId);
      if (this.isCurrentSend(generation, userId)) this.messages.set(history);
    } catch {
      // Keep the pending text and safe error visible when the service is unreachable.
    }
  }
}
