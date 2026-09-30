import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, Router } from '@angular/router';
import { of } from 'rxjs';
import { ChatPage } from './chat.page';
import { SidebarStore } from '../services/sidebar.store';
import { ChatStore } from '../services/chat.store';
import { conversation } from '../../../testing/fixtures';
import { AuthService } from '../../../core/auth/auth.service';

describe('lazy conversation entry', () => {
  let sidebar: {
    create: ReturnType<typeof vi.fn>;
    error: ReturnType<typeof signal<string | null>>;
  };
  let chat: {
    active: ReturnType<typeof signal<typeof conversation | null>>;
    queueFirstMessage: ReturnType<typeof vi.fn>;
    send: ReturnType<typeof vi.fn>;
    open: ReturnType<typeof vi.fn>;
    scrollRevision: ReturnType<typeof signal<number>>;
  };
  let router: { navigate: ReturnType<typeof vi.fn> };
  beforeEach(() => {
    sidebar = { create: vi.fn().mockResolvedValue(conversation), error: signal(null) };
    chat = {
      active: signal(null),
      queueFirstMessage: vi.fn(),
      send: vi.fn(),
      open: vi.fn().mockResolvedValue(undefined),
      scrollRevision: signal(0),
    };
    router = { navigate: vi.fn().mockResolvedValue(true) };
    TestBed.configureTestingModule({
      providers: [
        { provide: SidebarStore, useValue: sidebar },
        { provide: ChatStore, useValue: chat },
        { provide: Router, useValue: router },
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({})) } },
        { provide: AuthService, useValue: { currentUser: signal(null), logout: vi.fn() } },
      ],
    });
  });
  it('creates once on first send, queues original text, then navigates', async () => {
    const page = TestBed.createComponent(ChatPage).componentInstance;
    await page.submit('Buscame bife ancho para China');
    expect(sidebar.create).toHaveBeenCalledOnce();
    expect(chat.queueFirstMessage).toHaveBeenCalledWith(
      conversation.id,
      'Buscame bife ancho para China',
    );
    expect(router.navigate).toHaveBeenCalledWith(['/chat', conversation.id]);
    expect(chat.send).not.toHaveBeenCalled();
  });
  it('keeps creation retryable and never queues a failed first send', async () => {
    sidebar.create.mockResolvedValueOnce(null);
    sidebar.error.set('No disponible');
    const page = TestBed.createComponent(ChatPage).componentInstance;
    await page.submit('Mensaje original');
    expect(page.createError()).toBe('No disponible');
    expect(chat.queueFirstMessage).not.toHaveBeenCalled();
    await page.submit('Mensaje original');
    expect(sidebar.create).toHaveBeenCalledTimes(2);
    expect(chat.queueFirstMessage).toHaveBeenCalledWith(conversation.id, 'Mensaje original');
  });
  it('reuses the created conversation if navigation must be retried', async () => {
    router.navigate.mockResolvedValueOnce(false);
    const page = TestBed.createComponent(ChatPage).componentInstance;
    await page.submit('Mensaje original');
    expect(page.createError()).toContain('Reintentá');
    await page.submit('Mensaje original');
    expect(sidebar.create).toHaveBeenCalledOnce();
    expect(router.navigate).toHaveBeenCalledTimes(2);
  });
});
