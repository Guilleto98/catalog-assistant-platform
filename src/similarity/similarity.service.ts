import { HttpStatus, Injectable } from '@nestjs/common';
import { ApiError } from '../common/errors/api-error';
import { SIMILARITY_WEIGHTS } from '../common/metadata/field-metadata';
import type { ArticleDocument } from '../common/types/article.types';
import { getPath } from '../articles/article.mapper';
import { ArticlesService } from '../articles/articles.service';
import type { SimilarArticlesDto } from './dto/similar-articles.dto';

type Status = 'MATCH' | 'MISMATCH' | 'NOT_AVAILABLE';
interface EvaluatedCandidate {
  codigo: unknown;
  similarity_score: number;
  eligibility: 'ELIGIBLE' | 'INELIGIBLE';
  weighted_evaluation: Array<Record<string, unknown>>;
  required_evaluation: Array<Record<string, unknown>>;
}

@Injectable()
export class SimilarityService {
  constructor(private readonly articles: ArticlesService) {}

  async findSimilar(dto: SimilarArticlesDto): Promise<object> {
    if (!Number.isInteger(dto.limit) || dto.limit < 1 || dto.limit > 10) {
      throw new ApiError(
        'INVALID_SIMILARITY_REQUEST',
        'limit must be an integer between 1 and 10',
        HttpStatus.BAD_REQUEST,
      );
    }
    if ((dto.reference_code && dto.features) || (!dto.reference_code && !dto.features)) {
      throw new ApiError(
        'INVALID_SIMILARITY_REQUEST',
        'Provide reference_code or features, never both',
        HttpStatus.BAD_REQUEST,
      );
    }
    const weighted = dto.reference_code
      ? this.extractWeighted(await this.articles.findOne(dto.reference_code))
      : this.validateFeatures(dto.features!);
    const required = dto.required ?? {};
    Object.entries(required).forEach(([field, value]) =>
      this.articles.validateCriterion(field, value),
    );
    const documents = await this.articles.allDocuments();
    const evaluated = documents
      .filter(
        (article) => !dto.reference_code || article.identificacion.codigo !== dto.reference_code,
      )
      .map((article) => this.evaluate(article, weighted, required));
    const compare = (
      a: ReturnType<SimilarityService['evaluate']>,
      b: ReturnType<SimilarityService['evaluate']>,
    ): number =>
      b.similarity_score - a.similarity_score || String(a.codigo).localeCompare(String(b.codigo));
    const eligible = evaluated
      .filter((item) => item.eligibility === 'ELIGIBLE')
      .sort(compare)
      .slice(0, dto.limit);
    const ineligible = evaluated
      .filter((item) => item.eligibility === 'INELIGIBLE')
      .sort(compare)
      .slice(0, 10);
    return {
      criteria_used: { weighted, required },
      eligible_candidates: eligible,
      ineligible_candidates: ineligible,
    };
  }

  private validateFeatures(features: Record<string, unknown>): Record<string, unknown> {
    const entries = Object.entries(features);
    if (!entries.length)
      throw new ApiError(
        'INVALID_SIMILARITY_REQUEST',
        'features cannot be empty',
        HttpStatus.BAD_REQUEST,
      );
    const result: Record<string, unknown> = {};
    for (const [field, value] of entries) {
      if (!(field in SIMILARITY_WEIGHTS))
        throw new ApiError(
          'INVALID_SIMILARITY_REQUEST',
          `Field ${field} is not weighted`,
          HttpStatus.BAD_REQUEST,
        );
      this.articles.validateCriterion(field, value);
      result[field] = value;
    }
    return result;
  }

  private extractWeighted(article: ArticleDocument): Record<string, unknown> {
    return Object.fromEntries(
      Object.keys(SIMILARITY_WEIGHTS).map((field) => [field, getPath(article, field)]),
    );
  }

  private status(candidate: unknown, expected: unknown): Status {
    if (candidate === null || candidate === undefined) return 'NOT_AVAILABLE';
    return candidate === expected ? 'MATCH' : 'MISMATCH';
  }

  private evaluate(
    article: ArticleDocument,
    weighted: Record<string, unknown>,
    required: Record<string, unknown>,
  ): EvaluatedCandidate {
    let earned = 0;
    let maximum = 0;
    const weightedEvaluation = Object.entries(weighted).map(([field, expected]) => {
      const weight = SIMILARITY_WEIGHTS[field];
      const candidate = getPath(article, field);
      const status = this.status(candidate, expected);
      maximum += weight;
      if (status === 'MATCH') earned += weight;
      return {
        field,
        weight,
        reference_value: expected,
        candidate_value: candidate ?? null,
        status,
      };
    });
    const requiredEvaluation = Object.entries(required).map(([field, expected]) => {
      const candidate = getPath(article, field);
      return {
        field,
        required_value: expected,
        candidate_value: candidate ?? null,
        status: this.status(candidate, expected),
      };
    });
    const eligibility = requiredEvaluation.every((item) => item.status === 'MATCH')
      ? 'ELIGIBLE'
      : 'INELIGIBLE';
    return {
      codigo: article.identificacion.codigo,
      similarity_score: maximum ? Math.round((earned / maximum) * 10000) / 100 : 0,
      eligibility,
      weighted_evaluation: weightedEvaluation,
      required_evaluation: requiredEvaluation,
    };
  }
}
