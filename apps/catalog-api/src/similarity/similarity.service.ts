import { HttpStatus, Injectable } from '@nestjs/common';
import { ApiError } from '../common/errors/api-error';
import {
  API_ERROR_CODES,
  ARTICLE_ELIGIBILITY,
  SIMILARITY_POLICY,
  SIMILARITY_STATUS,
} from '../common/constants/api.constants';
import { SIMILARITY_WEIGHTS } from '../common/metadata/field-metadata';
import type { ArticleDocument } from '../common/types/article.types';
import { getPath } from '../articles/article.mapper';
import { ArticlesService } from '../articles/articles.service';
import type { SimilarArticlesDto } from './dto/similar-articles.dto';
import type {
  FindSimilarArticlesResponse,
  SimilarityCandidate,
  SimilarityEvaluation,
} from '../common/types/api-responses';

@Injectable()
export class SimilarityService {
  constructor(private readonly articles: ArticlesService) {}

  async findSimilar(dto: SimilarArticlesDto): Promise<FindSimilarArticlesResponse> {
    if (
      !Number.isInteger(dto.limit) ||
      dto.limit < SIMILARITY_POLICY.MIN_LIMIT ||
      dto.limit > SIMILARITY_POLICY.MAX_LIMIT
    ) {
      throw new ApiError(
        API_ERROR_CODES.INVALID_SIMILARITY_REQUEST,
        `limit must be an integer between ${SIMILARITY_POLICY.MIN_LIMIT} and ${SIMILARITY_POLICY.MAX_LIMIT}`,
        HttpStatus.BAD_REQUEST,
      );
    }
    if ((dto.reference_code && dto.features) || (!dto.reference_code && !dto.features)) {
      throw new ApiError(
        API_ERROR_CODES.INVALID_SIMILARITY_REQUEST,
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
    const compare = (a: SimilarityCandidate, b: SimilarityCandidate): number =>
      b.similarity_score - a.similarity_score || String(a.codigo).localeCompare(String(b.codigo));
    const eligible = evaluated
      .filter((item) => item.eligibility === ARTICLE_ELIGIBILITY.ELIGIBLE)
      .sort(compare)
      .slice(0, dto.limit);
    const ineligible = evaluated
      .filter((item) => item.eligibility === ARTICLE_ELIGIBILITY.INELIGIBLE)
      .sort(compare)
      .slice(0, SIMILARITY_POLICY.MAX_INELIGIBLE_CANDIDATES);
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
        API_ERROR_CODES.INVALID_SIMILARITY_REQUEST,
        'features cannot be empty',
        HttpStatus.BAD_REQUEST,
      );
    const result: Record<string, unknown> = {};
    for (const [field, value] of entries) {
      if (!(field in SIMILARITY_WEIGHTS))
        throw new ApiError(
          API_ERROR_CODES.INVALID_SIMILARITY_REQUEST,
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

  private status(candidate: unknown, expected: unknown): SimilarityEvaluation['status'] {
    if (candidate === null || candidate === undefined) return SIMILARITY_STATUS.NOT_AVAILABLE;
    return candidate === expected ? SIMILARITY_STATUS.MATCH : SIMILARITY_STATUS.MISMATCH;
  }

  private evaluate(
    article: ArticleDocument,
    weighted: Record<string, unknown>,
    required: Record<string, unknown>,
  ): SimilarityCandidate {
    let earned = 0;
    let maximum = 0;
    const weightedEvaluation = Object.entries(weighted).map(([field, expected]) => {
      const weight = SIMILARITY_WEIGHTS[field];
      const candidate = getPath(article, field);
      const status = this.status(candidate, expected);
      maximum += weight;
      if (status === SIMILARITY_STATUS.MATCH) earned += weight;
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
    const eligibility = requiredEvaluation.every((item) => item.status === SIMILARITY_STATUS.MATCH)
      ? ARTICLE_ELIGIBILITY.ELIGIBLE
      : ARTICLE_ELIGIBILITY.INELIGIBLE;
    const decimalFactor = 10 ** SIMILARITY_POLICY.SCORE_DECIMAL_PLACES;
    const scorePercent =
      maximum === 0 ? 0 : (earned / maximum) * SIMILARITY_POLICY.SCORE_PERCENT_BASE;
    return {
      codigo: article.identificacion.codigo,
      similarity_score: Math.round(scorePercent * decimalFactor) / decimalFactor,
      eligibility,
      weighted_evaluation: weightedEvaluation,
      required_evaluation: requiredEvaluation,
    };
  }
}
