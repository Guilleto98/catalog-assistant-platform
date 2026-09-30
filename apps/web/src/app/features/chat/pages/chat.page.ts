import {
  afterNextRender,
  Component,
  effect,
  ElementRef,
  inject,
  Injector,
  OnInit,
  signal,
  viewChild,
} from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ChatSidebar } from '../components/chat-sidebar';
import { ChatComposer } from '../components/chat-composer';
import { MessageBubble } from '../components/message-bubble';
import { ChatStore } from '../services/chat.store';
import { SidebarStore } from '../services/sidebar.store';
import { safeError } from '../../../core/api/errors';
import {
  CHAT_PAGINATION,
  CHAT_SCROLL_POLICY,
  CONVERSATION_STATUS,
  MESSAGE_ROLE,
} from '../../../core/constants/ui.constants';

@Component({
  selector: 'app-chat-page',
  imports: [ChatSidebar, ChatComposer, MessageBubble, RouterLink],
  template: ` <div
    class="chat-shell"
    [class.sidebar-open]="sidebarOpen()"
    [class.sidebar-collapsed]="sidebarCollapsed()"
  >
    <app-chat-sidebar
      [activeId]="chat.active()?.id || null"
      [collapsed]="sidebarCollapsed()"
      (collapse)="sidebarCollapsed.set(!sidebarCollapsed())"
      (newConversation)="newConversation()"
      (selected)="sidebarOpen.set(false)"
    />
    @if (sidebarOpen()) {
      <button
        class="sidebar-overlay"
        aria-label="Cerrar menú"
        (click)="sidebarOpen.set(false)"
      ></button>
    }
    <main class="chat-main">
      <header class="chat-header">
        <button
          class="menu-toggle"
          aria-label="Abrir conversaciones"
          (click)="sidebarOpen.set(!sidebarOpen())"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            aria-hidden="true"
          >
            <path d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        </button>
        <div>
          <h1>{{ chat.active()?.title || 'Tu espacio de consultas' }}</h1>
          <p>Asistente de artículos</p>
        </div>
        <span class="workspace-badge">Catálogo</span>
      </header>
      <section
        class="message-area"
        #messageArea
        (scroll)="onScroll()"
        (wheel)="scrollIntent()"
        (touchmove)="scrollIntent()"
        (pointerdown)="scrollIntent()"
        (keydown)="scrollIntent()"
        aria-label="Historial de conversación"
      >
        <div class="conversation-content">
          @if (chat.loading()) {
            <p class="loading-history" role="status">Cargando conversación…</p>
          } @else if (chat.loadError()) {
            <div class="empty-state">
              <h2>{{ chat.loadError() }}</h2>
              <a class="primary" routerLink="/chat">Volver al chat</a
              ><button (click)="reload()">Volver a intentar</button>
            </div>
          } @else if (!chat.active()) {
            <div class="empty-state">
              <img class="welcome-symbol" src="/brand/agrolink-symbol-smooth-3d.svg" alt="" />
              <p class="eyebrow">ASISTENTE DE ARTÍCULOS</p>
              <h2>Consultá tu catálogo.<br />Encontrá la alternativa correcta.</h2>
              <p>Buscá artículos, revisá sus características o compará opciones.</p>
              <div class="suggested-actions">
                <button (click)="submit('¿Qué funcionalidades tenés?')">
                  ¿Qué puedo consultar?</button
                ><button (click)="composer()?.openMenu()">Ver mis filtros</button>
              </div>
            </div>
          } @else {
            @if (!chat.messages().length && !chat.pending()) {
              <div class="empty-state">
                <img class="welcome-symbol" src="/brand/agrolink-symbol-smooth-3d.svg" alt="" />
                <h2>¿En qué puedo ayudarte?</h2>
                <p>Podés empezar con una búsqueda de artículos o consultar un código.</p>
              </div>
            }
            @for (message of chat.messages(); track message.id) {
              <app-message-bubble [message]="message" />
            }
            @if (chat.pending(); as pending) {
              @if (!pending.persistedId && !hasPendingInHistory()) {
                <article class="message user-message pending-message">
                  <header>
                    <strong>Vos</strong
                    ><span>{{ chat.sending() ? 'Enviando…' : 'Sin confirmar' }}</span>
                  </header>
                  <p class="message-text">{{ pending.request.text }}</p>
                </article>
              }
            }
            @if (chat.sending()) {
              <div class="thinking" role="status"><span>Pensando…</span><i></i></div>
            }
          }
        </div>
      </section>
      @if (!chat.loading() && !chat.loadError()) {
        <footer class="composer-area">
          @if (createError()) {
            <div class="send-error" role="alert">
              {{ createError() }}
              <button (click)="submit(composer()?.text || '')">Reintentar</button>
            </div>
          }
          @if (chat.sendError()) {
            <div class="send-error" role="alert">
              <p>{{ chat.sendError() }}</p>
              <button (click)="chat.retry()" [disabled]="chat.sending()">
                Consultar resultado / reintentar mismo envío
              </button>
              <button (click)="chat.dismissPending()" [disabled]="chat.sending()">
                Liberar envío y volver al chat
              </button>
            </div>
          }
          @if (chat.active()?.status === conversationStatus.ARCHIVED) {
            <p class="muted">Esta conversación está archivada y sólo permite lectura.</p>
          } @else {
            <app-chat-composer
              [disabled]="creating() || chat.sending() || !!chat.pending()"
              [clearOnSubmit]="!!chat.active()"
              (submitted)="submit($event)"
            />
          }
        </footer>
      }
    </main>
  </div>`,
})
export class ChatPage implements OnInit {
  readonly conversationStatus = CONVERSATION_STATUS;
  readonly chat = inject(ChatStore);
  readonly sidebar = inject(SidebarStore);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly injector = inject(Injector);
  readonly sidebarOpen = signal(false);
  readonly sidebarCollapsed = signal(false);
  readonly creating = signal(false);
  readonly createError = signal<string | null>(null);
  readonly composer = viewChild(ChatComposer);
  private readonly area = viewChild<ElementRef<HTMLElement>>('messageArea');
  private nearBottom = true;
  private userScrollUntil = 0;
  private previousConversation: string | null = null;
  private firstConversationId: string | null = null;
  constructor() {
    this.route.paramMap
      .pipe(takeUntilDestroyed())
      .subscribe((params) => void this.openConversation(params.get('conversationId')));
    effect(() => {
      this.chat.scrollRevision();
      const id = this.chat.active()?.id ?? null;
      const changed = id !== this.previousConversation;
      this.previousConversation = id;
      if (changed || this.nearBottom)
        afterNextRender(
          {
            write: () => {
              const element = this.area()?.nativeElement;
              if (element) element.scrollTop = element.scrollHeight;
            },
          },
          { injector: this.injector },
        );
    });
  }
  ngOnInit(): void {
    void this.sidebar.load();
  }
  onScroll(): void {
    if (Date.now() > this.userScrollUntil) return;
    const element = this.area()?.nativeElement;
    if (element)
      this.nearBottom =
        element.scrollHeight - element.scrollTop - element.clientHeight <
        CHAT_SCROLL_POLICY.BOTTOM_THRESHOLD_PX;
  }
  scrollIntent(): void {
    this.userScrollUntil = Date.now() + CHAT_SCROLL_POLICY.USER_INTENT_WINDOW_MS;
    requestAnimationFrame(() => this.onScroll());
  }
  reload(): void {
    void this.chat.open(this.route.snapshot.paramMap.get('conversationId'));
  }
  hasPendingInHistory(): boolean {
    // Reconciliation is only visual; the backend UUID remains the source of idempotency.
    const pending = this.chat.pending();
    return (
      !!pending &&
      this.chat.messages().at(-CHAT_PAGINATION.PAGE_INDEX_ORIGIN)?.role === MESSAGE_ROLE.USER &&
      this.chat.messages().at(-CHAT_PAGINATION.PAGE_INDEX_ORIGIN)?.text === pending.request.text
    );
  }
  private async openConversation(id: string | null): Promise<void> {
    await this.chat.open(id);
    if (id && this.chat.active()?.id === id) {
      const first = this.chat.takeFirstMessage(id);
      if (first) await this.chat.send(first);
    }
  }
  async submit(text: string): Promise<void> {
    if (!text.trim() || this.creating()) return;
    if (this.chat.active()) {
      await this.chat.send(text);
      return;
    }
    this.creating.set(true);
    this.createError.set(null);
    try {
      if (!this.firstConversationId) {
        const conversation = await this.sidebar.create();
        if (!conversation) {
          this.createError.set(this.sidebar.error() || 'No se pudo iniciar la conversación.');
          return;
        }
        this.firstConversationId = conversation.id;
        this.chat.queueFirstMessage(conversation.id, text);
      } else {
        this.chat.queueFirstMessage(this.firstConversationId, text);
      }
      this.sidebarOpen.set(false);
      if (!(await this.router.navigate(['/chat', this.firstConversationId])))
        this.createError.set('No se pudo abrir la conversación. Reintentá sin perder el mensaje.');
    } catch (error) {
      this.createError.set(safeError(error));
    } finally {
      this.creating.set(false);
    }
  }
  async newConversation(): Promise<void> {
    this.sidebarOpen.set(false);
    this.createError.set(null);
    this.firstConversationId = null;
    await this.router.navigateByUrl('/chat');
  }
}
