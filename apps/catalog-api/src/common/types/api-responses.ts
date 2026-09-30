import type { JsonScalar, SearchRequest } from './article.types';
import type {
  ArticleEligibility,
  FieldType,
  FilterOperator,
  SimilarityStatus,
} from '../constants/api.constants';

export interface ArticleSummary {
  codigo: string;
  nombre: string;
  corte: string;
  especie: string;
  mercado: string;
  pais_destino: string;
  temperatura: string;
  presentacion: string;
  envase_primario: string;
  envase_exterior: string | null;
  tipo_peso: string;
  peso_promedio_kg: number | null;
  activo: boolean;
  ficha_id: string | undefined;
}

export interface PaginationResponse {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface SearchArticlesResponse {
  items: ArticleSummary[];
  pagination: PaginationResponse;
  applied_filters: NonNullable<SearchRequest['filters']>;
  applied_sort: NonNullable<SearchRequest['sort']>;
}

export interface ArticleComparisonField {
  field: string;
  values: Record<string, JsonScalar | undefined>;
  different: boolean;
}

export interface CompareArticlesResponse {
  compared_codes: string[];
  fields: ArticleComparisonField[];
  different_fields_count: number;
  equal_fields_count: number;
}

export interface SimilarityEvaluation {
  field: string;
  status: SimilarityStatus;
  candidate_value: JsonScalar | null;
  reference_value?: unknown;
  required_value?: unknown;
  weight?: number;
}

export interface SimilarityCandidate {
  codigo: string;
  similarity_score: number;
  eligibility: ArticleEligibility;
  weighted_evaluation: SimilarityEvaluation[];
  required_evaluation: SimilarityEvaluation[];
}

export interface FindSimilarArticlesResponse {
  criteria_used: {
    weighted: Record<string, unknown>;
    required: Record<string, unknown>;
  };
  eligible_candidates: SimilarityCandidate[];
  ineligible_candidates: SimilarityCandidate[];
}

export interface TechnicalSheetResponse {
  ficha_id: string;
  articulo_codigo: string;
  titulo: string;
  version: string;
  idioma: string;
  estado: string;
  created_at: string;
  updated_at: string;
  source_note: string;
}

export interface SavedFilterResponse {
  id: string;
  owner_user_id: string;
  name: string;
  description: string | null;
  search: SearchRequest;
  created_at: string;
  updated_at: string;
}

export interface HealthResponse {
  status: string;
  dataset_version: string;
  articles: number;
}

export interface FilterableFieldResponse {
  path: string;
  type: FieldType;
  nullable: boolean;
  unit: string | null;
  operators: readonly FilterOperator[];
  used_for_similarity: boolean;
  can_be_required: boolean;
  allowed_values?: readonly (string | number | boolean)[];
}

export interface FilterableFieldsResponse {
  fields: FilterableFieldResponse[];
}
