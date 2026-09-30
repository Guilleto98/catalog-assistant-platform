import { Component, input } from '@angular/core';
import { UiEvent } from '../../../../api/contracts';
import { UI_EVENT_SCHEMA_VERSION, UI_EVENT_TYPE } from '../../../../core/constants/ui.constants';
import { ArticleSearchResults, ArticleDetail, ArticleComparison } from './catalog-views';
import { SimilarityResults } from './similarity-results';
import {
  TechnicalSheet,
  RequestDraft,
  SavedFilterList,
  SavedFilterCreated,
  SavedFilterDeleted,
  AttachmentStatus,
  EventError,
} from './support-views';

@Component({
  selector: 'app-ui-event-renderer',
  imports: [
    ArticleSearchResults,
    ArticleDetail,
    ArticleComparison,
    SimilarityResults,
    TechnicalSheet,
    RequestDraft,
    SavedFilterList,
    SavedFilterCreated,
    SavedFilterDeleted,
    AttachmentStatus,
    EventError,
  ],
  template: `@let item = event();
    @if (item.schemaVersion === schemaVersion) {
      @switch (item.type) {
        @case (eventType.ARTICLE_SEARCH_RESULTS) {
          <app-article-search-results [payload]="item.payload" />
        }
        @case (eventType.ARTICLE_DETAIL) {
          <app-article-detail [payload]="item.payload" />
        }
        @case (eventType.ARTICLE_COMPARISON) {
          <app-article-comparison [payload]="item.payload" />
        }
        @case (eventType.SIMILARITY_RESULTS) {
          <app-similarity-results [payload]="item.payload" />
        }
        @case (eventType.TECHNICAL_SHEET) {
          <app-technical-sheet [payload]="item.payload" />
        }
        @case (eventType.REQUEST_DRAFT) {
          <app-request-draft [payload]="item.payload" />
        }
        @case (eventType.SAVED_FILTER_LIST) {
          <app-saved-filter-list [payload]="item.payload" />
        }
        @case (eventType.SAVED_FILTER_CREATED) {
          <app-saved-filter-created [payload]="item.payload" />
        }
        @case (eventType.SAVED_FILTER_DELETED) {
          <app-saved-filter-deleted [payload]="item.payload" />
        }
        @case (eventType.ATTACHMENT_STATUS) {
          <app-attachment-status [payload]="item.payload" />
        }
        @case (eventType.ERROR) {
          <app-event-error [payload]="item.payload" />
        }
        @default {
          <p class="event-fallback">
            Este contenido no está disponible en esta versión de la aplicación.
          </p>
        }
      }
    } @else {
      <p class="event-fallback">
        Este contenido no está disponible en esta versión de la aplicación.
      </p>
    }`,
})
export class UiEventRenderer {
  readonly schemaVersion = UI_EVENT_SCHEMA_VERSION;
  readonly eventType = UI_EVENT_TYPE;
  readonly event = input.required<UiEvent>();
}
