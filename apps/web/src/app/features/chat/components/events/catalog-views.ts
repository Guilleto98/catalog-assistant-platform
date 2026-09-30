import { Component, input } from '@angular/core';
import { Payload } from '../../../../api/contracts';
import { COMPARISON_STATUS, LIST_PRESENTATION } from '../../../../core/constants/ui.constants';

@Component({
  selector: 'app-article-search-results',
  template: ` <section class="event-card" aria-label="Resultados de artículos">
    <header>
      <h3>Artículos encontrados</h3>
      <span class="badge">{{ payload().total }} resultados</span>
    </header>
    @for (article of payload().articles; track article.code; let position = $index) {
      <article class="article-result">
        <span class="result-number">{{ position + listPresentation.POSITION_ORIGIN }}</span>
        <div class="result-body">
          <strong>{{ article.code }}</strong>
          <h4>{{ article.name || 'Artículo' }}</h4>
          <div class="chips">
            @if (article.cut) {
              <span>{{ article.cut }}</span>
            }
            @if (article.market) {
              <span>{{ article.market }}</span>
            }
            @if (article.temperature) {
              <span>{{ article.temperature }}</span>
            }
            @if (article.presentation) {
              <span>{{ article.presentation }}</span>
            }
          </div>
        </div>
      </article>
    } @empty {
      <p>No se encontraron artículos con estos criterios.</p>
    }
    @if (payload().total > payload().articles.length) {
      <p class="muted">
        Se muestran {{ payload().articles.length }} de {{ payload().total }} resultados.
      </p>
    }
  </section>`,
})
export class ArticleSearchResults {
  readonly listPresentation = LIST_PRESENTATION;
  readonly payload = input.required<Payload<'ARTICLE_SEARCH_RESULTS'>>();
}

@Component({
  selector: 'app-article-detail',
  template: ` <section class="event-card" aria-label="Detalle del artículo">
    <header>
      <h3>{{ payload().article.name || 'Detalle del artículo' }}</h3>
      <span class="badge">{{ payload().article.code }}</span>
    </header>
    @for (group of payload().article.groups; track group.key) {
      <details class="detail-group" [open]="$first">
        <summary>{{ group.label }}</summary>
        <dl>
          @for (field of group.fields; track field.field) {
            <div>
              <dt>{{ field.label }}</dt>
              <dd>{{ field.displayValue }}</dd>
            </div>
          }
        </dl>
      </details>
    }
  </section>`,
})
export class ArticleDetail {
  readonly payload = input.required<Payload<'ARTICLE_DETAIL'>>();
}

@Component({
  selector: 'app-article-comparison',
  template: ` <section class="event-card" aria-label="Comparación de artículos">
    <h3>Comparación de artículos</h3>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Característica</th>
            @for (article of payload().articles; track article.code) {
              <th>
                {{ article.code }}<small>{{ article.name }}</small>
              </th>
            }
            <th>Resultado</th>
          </tr>
        </thead>
        <tbody>
          @for (row of payload().rows; track row.field) {
            <tr>
              <th>{{ row.label }}</th>
              @for (value of row.values; track value.articleCode) {
                <td>{{ value.displayValue }}</td>
              }
              <td>{{ row.status === comparisonStatus.SAME ? 'Igual' : 'Diferente' }}</td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  </section>`,
})
export class ArticleComparison {
  readonly comparisonStatus = COMPARISON_STATUS;
  readonly payload = input.required<Payload<'ARTICLE_COMPARISON'>>();
}
