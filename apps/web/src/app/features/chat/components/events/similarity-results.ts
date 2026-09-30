import { Component, input } from '@angular/core';
import { Payload } from '../../../../api/contracts';
import { SIMILARITY_STATUS } from '../../../../core/constants/ui.constants';

@Component({
  selector: 'app-similarity-results',
  template: ` <section class="event-card similarity" aria-label="Resultados de similitud">
    <h3>Alternativas por similitud</h3>
    <p class="muted">La aptitud depende de los requisitos obligatorios, no del puntaje.</p>
    <section class="eligible" aria-label="Aptos">
      <h4>
        Aptos <span class="badge">{{ payload().eligibleCandidates.length }}</span>
      </h4>
      @for (candidate of payload().eligibleCandidates; track candidate.article.code) {
        <article class="candidate">
          <div>
            <strong>{{ candidate.article.code }}</strong>
            <p>{{ candidate.article.name }}</p>
          </div>
          <span class="badge good">Apto</span><span>Similitud {{ candidate.score }}%</span>
          <details class="candidate-criteria">
            <summary>Ver criterios</summary>
            <ul>
              @for (criterion of candidate.criteria; track criterion.field) {
                <li>
                  <strong>{{ criterion.label }}</strong> ·
                  {{
                    criterion.status === similarityStatus.MATCH
                      ? 'Coincide'
                      : criterion.status === similarityStatus.MISMATCH
                        ? 'No coincide'
                        : 'Sin dato'
                  }}{{ criterion.required ? ' · Obligatorio' : ''
                  }}<small
                    >Solicitado: {{ criterion.expectedDisplayValue }} · Artículo:
                    {{ criterion.actualDisplayValue }}</small
                  >
                </li>
              }
            </ul>
          </details>
        </article>
      } @empty {
        <p>No hay alternativas aptas para los requisitos solicitados.</p>
      }
    </section>
    <section class="ineligible" aria-label="No aptos">
      <h4>
        No aptos <span class="badge">{{ payload().ineligibleCandidates.length }}</span>
      </h4>
      <p>
        No cumplen al menos un requisito obligatorio. No son alternativas aptas, aunque tengan un
        puntaje alto.
      </p>
      @for (candidate of payload().ineligibleCandidates; track candidate.article.code) {
        <article class="candidate">
          <div>
            <strong>{{ candidate.article.code }}</strong>
            <p>{{ candidate.article.name }}</p>
          </div>
          <span class="badge bad">No apto</span><span>Similitud {{ candidate.score }}%</span>
          <p class="required-warning">
            @for (criterion of candidate.criteria; track criterion.field) {
              @if (criterion.required && criterion.status !== similarityStatus.MATCH) {
                <span
                  >{{ criterion.label }}:
                  {{ criterion.status === similarityStatus.MISMATCH ? 'no coincide' : 'sin dato' }}
                  · Obligatorio</span
                >
              }
            }
          </p>
          <details class="candidate-criteria">
            <summary>Ver criterios</summary>
            <ul>
              @for (criterion of candidate.criteria; track criterion.field) {
                <li>
                  <strong>{{ criterion.label }}</strong> ·
                  {{
                    criterion.status === similarityStatus.MATCH
                      ? 'Coincide'
                      : criterion.status === similarityStatus.MISMATCH
                        ? 'No coincide'
                        : 'Sin dato'
                  }}{{ criterion.required ? ' · Obligatorio' : ''
                  }}<small
                    >Solicitado: {{ criterion.expectedDisplayValue }} · Artículo:
                    {{ criterion.actualDisplayValue }}</small
                  >
                </li>
              }
            </ul>
          </details>
        </article>
      }
    </section>
  </section>`,
})
export class SimilarityResults {
  readonly similarityStatus = SIMILARITY_STATUS;
  readonly payload = input.required<Payload<'SIMILARITY_RESULTS'>>();
}
