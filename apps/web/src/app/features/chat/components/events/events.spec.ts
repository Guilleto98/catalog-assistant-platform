import { TestBed } from '@angular/core/testing';
import { UiEventRenderer } from './ui-event-renderer';
import { events } from '../../../../testing/events.generated';
import { UiEvent } from '../../../../api/contracts';

describe('UiEventRenderer public contracts', () => {
  for (const event of events) {
    it(`renders ${event.type} without guessing data from narrative`, async () => {
      const fixture = TestBed.createComponent(UiEventRenderer);
      fixture.componentRef.setInput('event', event);
      await fixture.whenStable();
      const element: HTMLElement = fixture.nativeElement;
      expect(element.querySelector('section')).not.toBeNull();
      expect(element.querySelector('.event-fallback')).toBeNull();
    });
  }
  it('unknown type has safe fallback', async () => {
    const fixture = TestBed.createComponent(UiEventRenderer);
    fixture.componentRef.setInput('event', { ...events[0], type: 'FUTURE_EVENT' });
    await fixture.whenStable();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('no está disponible');
  });
  it('unknown schemaVersion has safe fallback', async () => {
    const fixture = TestBed.createComponent(UiEventRenderer);
    fixture.componentRef.setInput('event', { ...events[0], schemaVersion: 99 });
    await fixture.whenStable();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('no está disponible');
  });
  it('90 INELIGIBLE never appears among 70 ELIGIBLE', async () => {
    const fixture = TestBed.createComponent(UiEventRenderer);
    const event = events.find((item) => item.type === 'SIMILARITY_RESULTS')!;
    fixture.componentRef.setInput('event', event);
    await fixture.whenStable();
    const element: HTMLElement = fixture.nativeElement;
    expect(element.querySelector('.eligible')?.textContent).toContain('900006');
    expect(element.querySelector('.eligible')?.textContent).not.toContain('900004');
    expect(element.querySelector('.ineligible')?.textContent).toContain('900004');
    expect(element.querySelector('.ineligible')?.textContent).toContain('90%');
  });
  it('HTML in catalog strings stays inert text', async () => {
    const event = structuredClone(events[0]) as Extract<
      UiEvent,
      { type: 'ARTICLE_SEARCH_RESULTS' }
    >;
    event.payload.articles[0].name = '<img src=x onerror=alert(1)>';
    const fixture = TestBed.createComponent(UiEventRenderer);
    fixture.componentRef.setInput('event', event);
    await fixture.whenStable();
    const element: HTMLElement = fixture.nativeElement;
    expect(element.querySelector('img')).toBeNull();
    expect(element.textContent).toContain('<img src=x');
  });
  it('a metadata-only technical sheet does not offer fake download', async () => {
    const fixture = TestBed.createComponent(UiEventRenderer);
    fixture.componentRef.setInput(
      'event',
      events.find((item) => item.type === 'TECHNICAL_SHEET'),
    );
    await fixture.whenStable();
    const element: HTMLElement = fixture.nativeElement;
    expect(element.querySelector('a,button')).toBeNull();
  });
  it('search cards keep sequence and only compact article information', async () => {
    const fixture = TestBed.createComponent(UiEventRenderer);
    fixture.componentRef.setInput(
      'event',
      events.find((item) => item.type === 'ARTICLE_SEARCH_RESULTS'),
    );
    await fixture.whenStable();
    const element: HTMLElement = fixture.nativeElement;
    expect(element.querySelector('.result-number')?.textContent?.trim()).toBe('1');
    expect(element.querySelector('.chips')?.textContent).toContain('SIN_HUESO');
  });
  it('article detail groups are navigable and secondary groups begin collapsed', async () => {
    const fixture = TestBed.createComponent(UiEventRenderer);
    fixture.componentRef.setInput(
      'event',
      events.find((item) => item.type === 'ARTICLE_DETAIL'),
    );
    await fixture.whenStable();
    const groups = (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLDetailsElement>(
      '.detail-group',
    );
    expect(groups.length).toBeGreaterThan(1);
    expect(groups[0].open).toBe(true);
    expect(groups[1].open).toBe(false);
  });
  it('comparison exposes a textual difference state', async () => {
    const fixture = TestBed.createComponent(UiEventRenderer);
    fixture.componentRef.setInput(
      'event',
      events.find((item) => item.type === 'ARTICLE_COMPARISON'),
    );
    await fixture.whenStable();
    expect((fixture.nativeElement as HTMLElement).querySelector('table')?.textContent).toContain(
      'Diferente',
    );
  });
  it('draft fields translate statuses and expose safe provenance', async () => {
    const fixture = TestBed.createComponent(UiEventRenderer);
    fixture.componentRef.setInput(
      'event',
      events.find((item) => item.type === 'REQUEST_DRAFT'),
    );
    await fixture.whenStable();
    const text = (fixture.nativeElement as HTMLElement).textContent || '';
    expect(text).toContain('Propuesto');
    expect(text).toContain('Pedido · B2');
    expect(text).not.toContain('attachmentId');
    const pdf = structuredClone(events.find((item) => item.type === 'REQUEST_DRAFT')) as Extract<
      UiEvent,
      { type: 'REQUEST_DRAFT' }
    >;
    pdf.payload.fields[0].source = { type: 'PDF', attachmentId: 'private-id', page: 3 };
    fixture.componentRef.setInput('event', pdf);
    await fixture.whenStable();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Página 3');
    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('private-id');
  });
});
