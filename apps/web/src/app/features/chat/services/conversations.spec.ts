import { TestBed } from '@angular/core/testing';
import { HttpErrorResponse, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { API_BASE_URL } from '../../../core/api/config';
import { apiInterceptor } from '../../../core/api/interceptor';
import { AuthService } from '../../../core/auth/auth.service';
import { ConversationsService } from './conversations.service';
import { ChatStore } from './chat.store';
import { SidebarStore } from './sidebar.store';
import { conversation, message, sent, user } from '../../../testing/fixtures';

describe('Conversation API and state', () => {
  let http: HttpTestingController;
  let api: ConversationsService;
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([apiInterceptor])),
        provideHttpClientTesting(),
        { provide: API_BASE_URL, useValue: '/api/v1' },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    api = TestBed.inject(ConversationsService);
    const auth = TestBed.inject(AuthService);
    auth.currentUser.set(user);
    auth.status.set('ready');
  });
  afterEach(() => http.verify());
  it('maps list without changing backend order and passes pagination', async () => {
    const promise = api.listConversations(2, 20);
    const request = http.expectOne('/api/v1/conversations?page=2&pageSize=20');
    expect(request.request.withCredentials).toBe(true);
    request.flush({ items: [conversation], page: 2, pageSize: 20, total: 21 });
    expect((await promise).items).toEqual([conversation]);
  });
  it('creates conversation using Application API', async () => {
    const promise = api.createConversation();
    const request = http.expectOne('/api/v1/conversations');
    expect(request.request.method).toBe('POST');
    request.flush(conversation);
    expect(await promise).toEqual(conversation);
  });
  it('reads saved filters only through authenticated Application API', async () => {
    const promise = api.listSavedFilters();
    const request = http.expectOne('/api/v1/saved-filters');
    expect(request.request.method).toBe('GET');
    expect(request.request.withCredentials).toBe(true);
    request.flush({ filters: [] });
    expect(await promise).toEqual({ filters: [] });
  });
  it('loads metadata plus every history page in ASC order', async () => {
    const chat = TestBed.inject(ChatStore);
    TestBed.tick();
    const promise = chat.open('c1');
    http.expectOne('/api/v1/conversations/c1').flush(conversation);
    http
      .expectOne('/api/v1/conversations/c1/messages?page=1&pageSize=100')
      .flush({ items: [message], page: 1, pageSize: 1, total: 2 });
    await Promise.resolve();
    http
      .expectOne('/api/v1/conversations/c1/messages?page=2&pageSize=100')
      .flush({ items: [{ ...message, id: 'm2' }], page: 2, pageSize: 1, total: 2 });
    await promise;
    expect(chat.messages().map((m) => m.id)).toEqual(['m1', 'm2']);
  });
  it('sends one UUID and reuses it for retry without duplicate messages', async () => {
    const chat = TestBed.inject(ChatStore);
    TestBed.tick();
    chat.active.set(conversation);
    vi.spyOn(TestBed.inject(SidebarStore), 'load').mockResolvedValue();
    const send = vi
      .spyOn(api, 'sendMessage')
      .mockRejectedValueOnce(new HttpErrorResponse({ status: 0 }))
      .mockResolvedValueOnce(sent);
    vi.spyOn(api, 'getMessages').mockResolvedValue({
      items: [message],
      page: 1,
      pageSize: 100,
      total: 1,
    });
    const first = chat.send('China');
    const duplicate = chat.send('China');
    await Promise.all([first, duplicate]);
    expect(send).toHaveBeenCalledTimes(1);
    const request = send.mock.calls[0][1];
    expect(request.clientMessageId).toMatch(/^[0-9a-f-]{36}$/);
    await chat.retry();
    expect(send.mock.calls[1][1]).toEqual(request);
    expect(chat.messages().map((m) => m.id)).toEqual(['m1', 'm2']);
    expect(chat.pending()).toBeNull();
  });
  it('does not manufacture an assistant for a failed run', async () => {
    const chat = TestBed.inject(ChatStore);
    TestBed.tick();
    chat.active.set(conversation);
    vi.spyOn(TestBed.inject(SidebarStore), 'load').mockResolvedValue();
    vi.spyOn(api, 'sendMessage').mockResolvedValue({
      ...sent,
      assistantMessage: null,
      run: {
        id: 'r',
        status: 'FAILED',
        error: { code: 'AGENT_EXECUTION_FAILED', message: 'No disponible' },
      },
    });
    await chat.send('China');
    expect(chat.messages()).toEqual([message]);
    expect(chat.pending()).not.toBeNull();
    expect(chat.sendError()).toContain('registrada');
  });
  it('does not show a late response from another conversation', async () => {
    const chat = TestBed.inject(ChatStore);
    TestBed.tick();
    chat.active.set(conversation);
    let resolve!: (value: typeof sent) => void;
    vi.spyOn(api, 'sendMessage').mockImplementation(
      () =>
        new Promise((r) => {
          resolve = r;
        }),
    );
    const promise = chat.send('China');
    chat.clear();
    chat.active.set({ ...conversation, id: 'c2' });
    resolve(sent);
    await promise;
    expect(chat.messages()).toEqual([]);
  });
  it('clears sidebar and pending text on session invalidation', () => {
    const chat = TestBed.inject(ChatStore);
    const sidebar = TestBed.inject(SidebarStore);
    TestBed.tick();
    chat.messages.set([message]);
    sidebar.conversations.set([conversation]);
    TestBed.inject(AuthService).currentUser.set(null);
    TestBed.tick();
    expect(chat.messages()).toEqual([]);
    expect(sidebar.conversations()).toEqual([]);
  });
  it('safe not found leaves no active conversation', async () => {
    const chat = TestBed.inject(ChatStore);
    TestBed.tick();
    vi.spyOn(api, 'getConversation').mockRejectedValue(
      new HttpErrorResponse({ status: 404, url: '/api/v1/conversations/missing' }),
    );
    vi.spyOn(api, 'getMessages').mockResolvedValue({ items: [], page: 1, pageSize: 100, total: 0 });
    await chat.open('missing');
    expect(chat.loadError()).toBe('Conversación no encontrada.');
    expect(chat.active()).toBeNull();
  });
});
