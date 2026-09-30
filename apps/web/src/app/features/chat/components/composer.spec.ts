import { TestBed } from '@angular/core/testing';
import { ChatComposer } from './chat-composer';
import { ConversationsService } from '../services/conversations.service';
import { SavedFilterCommandMenu } from './saved-filter-command-menu';
import { SavedFilter } from '../../../api/contracts';
describe('ChatComposer', () => {
  const filters = [
    {
      id: 'filter-china',
      name: 'China congelados',
      criteria: { filters: [] },
      createdAt: '2026-01-01T00:00:00Z',
      updatedAt: '2026-01-01T00:00:00Z',
    },
    {
      id: 'filter-brasil',
      name: 'Brasil refrigerados',
      criteria: { filters: [] },
      createdAt: '2026-01-01T00:00:00Z',
      updatedAt: '2026-01-01T00:00:00Z',
    },
  ] as SavedFilter[];
  beforeEach(() =>
    TestBed.configureTestingModule({
      providers: [
        {
          provide: ConversationsService,
          useValue: { listSavedFilters: vi.fn().mockResolvedValue({ filters }) },
        },
      ],
    }),
  );
  it('Enter sends and Shift+Enter keeps multiline', () => {
    const fixture = TestBed.createComponent(ChatComposer);
    const component = fixture.componentInstance;
    const emit = vi.spyOn(component.submitted, 'emit');
    component.text = 'Consulta';
    component.keyDown(new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true }));
    expect(emit).not.toHaveBeenCalled();
    component.keyDown(new KeyboardEvent('keydown', { key: 'Enter' }));
    expect(emit).toHaveBeenCalledWith('Consulta');
  });
  it('disabled composer prevents duplicate sends', () => {
    const fixture = TestBed.createComponent(ChatComposer);
    fixture.componentRef.setInput('disabled', true);
    const emit = vi.spyOn(fixture.componentInstance.submitted, 'emit');
    fixture.componentInstance.text = 'Consulta';
    fixture.componentInstance.send();
    expect(emit).not.toHaveBeenCalled();
  });
  it('retains the first message when clearing is deferred for conversation creation', () => {
    const fixture = TestBed.createComponent(ChatComposer);
    fixture.componentRef.setInput('clearOnSubmit', false);
    const emit = vi.spyOn(fixture.componentInstance.submitted, 'emit');
    fixture.componentInstance.text = 'Buscame bife ancho';
    fixture.componentInstance.send();
    expect(emit).toHaveBeenCalledOnce();
    expect(fixture.componentInstance.text).toBe('Buscame bife ancho');
  });
  it('opens one palette from button or initial slash, not an inline slash', () => {
    const fixture = TestBed.createComponent(ChatComposer);
    const composer = fixture.componentInstance;
    composer.text = '10/20';
    composer.onInput();
    expect(composer.menuOpen()).toBe(false);
    composer.text = '/';
    composer.onInput();
    expect(composer.menuOpen()).toBe(true);
    composer.keyDown(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(composer.menuOpen()).toBe(false);
    composer.toggleMenu();
    expect(composer.menuOpen()).toBe(true);
  });
  it('loads real DTOs, filters locally and navigates with keyboard', async () => {
    const fixture = TestBed.createComponent(SavedFilterCommandMenu);
    const menu = fixture.componentInstance;
    await menu.load();
    expect(menu.visible().map((item) => item.id)).toEqual(['filter-china', 'filter-brasil']);
    menu.move(1);
    expect(menu.active()).toBe(1);
    const selected = vi.spyOn(menu.selected, 'emit');
    menu.choose();
    expect(selected).toHaveBeenCalledWith(filters[1]);
    fixture.componentRef.setInput('query', 'china');
    fixture.detectChanges();
    expect(menu.visible().map((item) => item.id)).toEqual(['filter-china']);
  });
  it('shows a genuine empty-filter state', async () => {
    const fixture = TestBed.createComponent(SavedFilterCommandMenu);
    vi.spyOn(TestBed.inject(ConversationsService), 'listSavedFilters').mockResolvedValue({
      filters: [],
    });
    await fixture.componentInstance.load();
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain(
      'Todavía no tenés filtros',
    );
  });
});
