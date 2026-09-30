import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import {
  ARTICLE_ELIGIBILITY,
  FIELD_TYPES,
  FILTER_OPERATOR_VALUES,
  SIMILARITY_STATUS,
  SORT_DIRECTION_VALUES,
} from '../constants/api.constants';
import type { SearchRequest } from '../types/article.types';
import type {
  ArticleSummary,
  CompareArticlesResponse,
  FilterableFieldResponse,
  FilterableFieldsResponse,
  FindSimilarArticlesResponse,
  HealthResponse,
  SavedFilterResponse,
  SearchArticlesResponse,
  SimilarityCandidate,
  SimilarityEvaluation,
  TechnicalSheetResponse,
} from '../types/api-responses';
import { SearchArticlesDto } from '../../articles/dto/search-articles.dto';

const JSON_SCALAR_SCHEMA = {
  oneOf: [
    { type: 'string' },
    { type: 'number' },
    { type: 'boolean' },
    { type: 'string', nullable: true },
  ],
};

export class ArticleSummaryResponseDto implements ArticleSummary {
  @ApiProperty() codigo!: string;
  @ApiProperty() nombre!: string;
  @ApiProperty() corte!: string;
  @ApiProperty() especie!: string;
  @ApiProperty() mercado!: string;
  @ApiProperty() pais_destino!: string;
  @ApiProperty() temperatura!: string;
  @ApiProperty() presentacion!: string;
  @ApiProperty() envase_primario!: string;
  @ApiProperty({ nullable: true }) envase_exterior!: string | null;
  @ApiProperty() tipo_peso!: string;
  @ApiProperty({ type: Number, nullable: true }) peso_promedio_kg!: number | null;
  @ApiProperty() activo!: boolean;
  @ApiPropertyOptional() ficha_id!: string | undefined;
}

export class PaginationResponseDto {
  @ApiProperty({ type: Number }) page!: number;
  @ApiProperty({ type: Number }) page_size!: number;
  @ApiProperty({ type: Number }) total_items!: number;
  @ApiProperty({ type: Number }) total_pages!: number;
}

export class AppliedFilterResponseDto {
  @ApiProperty() field!: string;
  @ApiProperty({ enum: FILTER_OPERATOR_VALUES })
  operator!: NonNullable<SearchRequest['filters']>[number]['operator'];
  @ApiPropertyOptional({
    oneOf: [...JSON_SCALAR_SCHEMA.oneOf, { type: 'array', items: JSON_SCALAR_SCHEMA }],
  })
  value?: unknown;
}

export class AppliedSortResponseDto {
  @ApiProperty() field!: string;
  @ApiProperty({ enum: SORT_DIRECTION_VALUES })
  direction!: NonNullable<SearchRequest['sort']>[number]['direction'];
}

export class SearchArticlesResponseDto implements SearchArticlesResponse {
  @ApiProperty({ type: [ArticleSummaryResponseDto] }) items!: ArticleSummaryResponseDto[];
  @ApiProperty({ type: PaginationResponseDto }) pagination!: PaginationResponseDto;
  @ApiProperty({ type: [AppliedFilterResponseDto] })
  applied_filters!: NonNullable<SearchRequest['filters']>;
  @ApiProperty({ type: [AppliedSortResponseDto] })
  applied_sort!: NonNullable<SearchRequest['sort']>;
}

export class ArticleDocumentResponseDto {
  @ApiProperty({ type: 'object', additionalProperties: JSON_SCALAR_SCHEMA })
  identificacion!: object;
  @ApiProperty({ type: 'object', additionalProperties: JSON_SCALAR_SCHEMA })
  producto_destino!: object;
  @ApiProperty({ type: 'object', additionalProperties: JSON_SCALAR_SCHEMA })
  codigos_asociaciones!: object;
  @ApiProperty({ type: 'object', additionalProperties: JSON_SCALAR_SCHEMA }) envase_pesaje!: object;
  @ApiProperty({ type: 'object', additionalProperties: JSON_SCALAR_SCHEMA }) etiquetado!: object;
  @ApiProperty({ type: 'object', additionalProperties: JSON_SCALAR_SCHEMA })
  fechas_operacion!: object;
  @ApiProperty({ type: 'object', additionalProperties: JSON_SCALAR_SCHEMA })
  comercial_operativo!: object;
  @ApiProperty({ type: 'object', additionalProperties: JSON_SCALAR_SCHEMA })
  calidad_seguridad!: object;
  @ApiProperty({ type: 'object', additionalProperties: JSON_SCALAR_SCHEMA }) metadata!: object;
  @ApiPropertyOptional() ficha_id?: string;
}

export class ArticleComparisonFieldDto {
  @ApiProperty() field!: string;
  @ApiProperty({ type: 'object', additionalProperties: JSON_SCALAR_SCHEMA })
  values!: CompareArticlesResponse['fields'][number]['values'];
  @ApiProperty() different!: boolean;
}

export class CompareArticlesResponseDto implements CompareArticlesResponse {
  @ApiProperty({ type: [String] }) compared_codes!: string[];
  @ApiProperty({ type: [ArticleComparisonFieldDto] }) fields!: ArticleComparisonFieldDto[];
  @ApiProperty({ type: Number }) different_fields_count!: number;
  @ApiProperty({ type: Number }) equal_fields_count!: number;
}

export class SimilarityEvaluationDto implements SimilarityEvaluation {
  @ApiProperty() field!: string;
  @ApiProperty({ enum: Object.values(SIMILARITY_STATUS) }) status!: SimilarityEvaluation['status'];
  @ApiProperty({ oneOf: JSON_SCALAR_SCHEMA.oneOf })
  candidate_value!: SimilarityEvaluation['candidate_value'];
  @ApiPropertyOptional({ oneOf: JSON_SCALAR_SCHEMA.oneOf }) reference_value?: unknown;
  @ApiPropertyOptional({ oneOf: JSON_SCALAR_SCHEMA.oneOf }) required_value?: unknown;
  @ApiPropertyOptional({ type: Number }) weight?: number;
}

export class SimilarityCandidateDto implements SimilarityCandidate {
  @ApiProperty() codigo!: string;
  @ApiProperty({ type: Number }) similarity_score!: number;
  @ApiProperty({ enum: Object.values(ARTICLE_ELIGIBILITY) })
  eligibility!: SimilarityCandidate['eligibility'];
  @ApiProperty({ type: [SimilarityEvaluationDto] })
  weighted_evaluation!: SimilarityEvaluationDto[];
  @ApiProperty({ type: [SimilarityEvaluationDto] })
  required_evaluation!: SimilarityEvaluationDto[];
}

export class FindSimilarArticlesResponseDto implements FindSimilarArticlesResponse {
  @ApiProperty({ type: 'object', additionalProperties: true })
  criteria_used!: FindSimilarArticlesResponse['criteria_used'];
  @ApiProperty({ type: [SimilarityCandidateDto] }) eligible_candidates!: SimilarityCandidateDto[];
  @ApiProperty({ type: [SimilarityCandidateDto] }) ineligible_candidates!: SimilarityCandidateDto[];
}

export class TechnicalSheetResponseDto implements TechnicalSheetResponse {
  @ApiProperty() ficha_id!: string;
  @ApiProperty() articulo_codigo!: string;
  @ApiProperty() titulo!: string;
  @ApiProperty() version!: string;
  @ApiProperty() idioma!: string;
  @ApiProperty() estado!: string;
  @ApiProperty({ format: 'date-time' }) created_at!: string;
  @ApiProperty({ format: 'date-time' }) updated_at!: string;
  @ApiProperty() source_note!: string;
}

export class SavedFilterResponseDto implements SavedFilterResponse {
  @ApiProperty() id!: string;
  @ApiProperty() owner_user_id!: string;
  @ApiProperty() name!: string;
  @ApiProperty({ nullable: true }) description!: string | null;
  @ApiProperty({ type: SearchArticlesDto }) search!: SearchRequest;
  @ApiProperty({ format: 'date-time' }) created_at!: string;
  @ApiProperty({ format: 'date-time' }) updated_at!: string;
}

export class HealthResponseDto implements HealthResponse {
  @ApiProperty() status!: string;
  @ApiProperty() dataset_version!: string;
  @ApiProperty({ type: Number }) articles!: number;
}

export class FilterableFieldResponseDto implements FilterableFieldResponse {
  @ApiProperty() path!: string;
  @ApiProperty({ enum: Object.values(FIELD_TYPES) })
  type!: FilterableFieldsResponse['fields'][number]['type'];
  @ApiProperty() nullable!: boolean;
  @ApiProperty({ nullable: true }) unit!: string | null;
  @ApiProperty({ enum: FILTER_OPERATOR_VALUES, isArray: true })
  operators!: FilterableFieldsResponse['fields'][number]['operators'];
  @ApiProperty() used_for_similarity!: boolean;
  @ApiProperty() can_be_required!: boolean;
  @ApiPropertyOptional({ type: [Object] }) allowed_values?: readonly (string | number | boolean)[];
}

export class FilterableFieldsResponseDto implements FilterableFieldsResponse {
  @ApiProperty({ type: [FilterableFieldResponseDto] }) fields!: FilterableFieldsResponse['fields'];
}
