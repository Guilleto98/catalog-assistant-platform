import { Component, input } from '@angular/core';
import { Payload } from '../../../../api/contracts';
import {
  DOCUMENT_SOURCE_TYPE,
  DRAFT_FIELD_STATUS,
  DRAFT_STATUS,
} from '../../../../core/constants/ui.constants';

@Component({
  selector: 'app-technical-sheet',
  template: ` <section class="event-card" aria-label="Ficha técnica">
    <h3>{{ payload().sheet.title || 'Ficha técnica' }}</h3>
    <dl>
      <div>
        <dt>Artículo</dt>
        <dd>{{ payload().sheet.articleCode }}</dd>
      </div>
      <div>
        <dt>Versión</dt>
        <dd>{{ payload().sheet.version || 'No disponible' }}</dd>
      </div>
      <div>
        <dt>Idioma</dt>
        <dd>{{ payload().sheet.language || 'No disponible' }}</dd>
      </div>
      <div>
        <dt>Estado</dt>
        <dd>{{ payload().sheet.status || 'No disponible' }}</dd>
      </div>
    </dl>
    @if (!payload().sheet.documentAvailable) {
      <p class="muted">Información de la ficha. No hay un documento descargable disponible.</p>
    }
    @if (payload().sheet.sourceNote) {
      <p>{{ payload().sheet.sourceNote }}</p>
    }
  </section>`,
})
export class TechnicalSheet {
  readonly payload = input.required<Payload<'TECHNICAL_SHEET'>>();
}

@Component({
  selector: 'app-request-draft',
  template: ` <section class="event-card" aria-label="Borrador de solicitud">
    <header>
      <h3>Borrador de solicitud</h3>
      <span class="badge">{{
        payload().status === draftStatus.DRAFT
          ? 'Borrador'
          : payload().status === draftStatus.READY
            ? 'Listo'
            : 'Requiere revisión'
      }}</span>
    </header>
    <p class="muted">Vista de consulta. La edición guiada se incorporará más adelante.</p>
    <dl>
      @for (field of payload().fields; track field.field) {
        <div>
          <dt>{{ field.label }}</dt>
          <dd>
            {{ field.displayValue }}
            <small
              >{{
                field.status === draftFieldStatus.PROPOSED
                  ? 'Propuesto'
                  : field.status === draftFieldStatus.CONFIRMED
                    ? 'Confirmado'
                    : field.status === draftFieldStatus.CORRECTED
                      ? 'Corregido'
                      : field.status === draftFieldStatus.REJECTED
                        ? 'Descartado'
                        : 'Requiere revisión'
              }}{{ field.required ? ' · Obligatorio' : '' }}</small
            >
            <small>{{
              field.source.type === documentSourceType.PDF
                ? 'Página ' + field.source.page
                : field.source.type === documentSourceType.SPREADSHEET
                  ? field.source.sheet + ' · ' + field.source.cell
                  : 'Corregido por usuario'
            }}</small>
          </dd>
        </div>
      }
    </dl>
  </section>`,
})
export class RequestDraft {
  readonly draftStatus = DRAFT_STATUS;
  readonly draftFieldStatus = DRAFT_FIELD_STATUS;
  readonly documentSourceType = DOCUMENT_SOURCE_TYPE;
  readonly payload = input.required<Payload<'REQUEST_DRAFT'>>();
}

@Component({
  selector: 'app-saved-filter-list',
  template: ` <section class="event-card" aria-label="Filtros guardados">
    <h3>Filtros guardados</h3>
    @for (filter of payload().filters; track filter.id) {
      <article class="article-result">
        <h4>{{ filter.name }}</h4>
        @for (criterion of filter.criteria.filters; track $index) {
          <p>{{ criterion.label }}: {{ criterion.displayValue }}</p>
        }
      </article>
    } @empty {
      <p>No hay filtros guardados.</p>
    }
  </section>`,
})
export class SavedFilterList {
  readonly payload = input.required<Payload<'SAVED_FILTER_LIST'>>();
}

@Component({
  selector: 'app-saved-filter-created',
  template: `<section class="event-card">
    <h3>Filtro guardado</h3>
    <p>{{ payload().filter.name }}</p>
  </section>`,
})
export class SavedFilterCreated {
  readonly payload = input.required<Payload<'SAVED_FILTER_CREATED'>>();
}

@Component({
  selector: 'app-saved-filter-deleted',
  template: `<section class="event-card">
    <h3>Filtro eliminado</h3>
    <p>{{ payload().name }}</p>
  </section>`,
})
export class SavedFilterDeleted {
  readonly payload = input.required<Payload<'SAVED_FILTER_DELETED'>>();
}

@Component({
  selector: 'app-attachment-status',
  template: `<section class="event-card" aria-label="Estado del adjunto">
    <h3>{{ payload().attachment.filename }}</h3>
    <p>{{ payload().attachment.type }} · {{ payload().attachment.status }}</p>
    @if (payload().attachment.error) {
      <p class="error">{{ payload().attachment.error?.message }}</p>
    }
  </section>`,
})
export class AttachmentStatus {
  readonly payload = input.required<Payload<'ATTACHMENT_STATUS'>>();
}

@Component({
  selector: 'app-event-error',
  template: `<section class="event-card error" role="alert">
    <h3>No se pudo completar la consulta</h3>
    <p>{{ payload().message }}</p>
  </section>`,
})
export class EventError {
  readonly payload = input.required<Payload<'ERROR'>>();
}
