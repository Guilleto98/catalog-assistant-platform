import type { FilterOperator, SortDirection } from '../constants/api.constants';

export type JsonScalar = string | number | boolean | null;
export type ArticleGroup = Record<string, JsonScalar>;

export interface IdentificationGroup extends ArticleGroup {
  codigo: string;
  nombre: string;
  especie: string;
  activo: boolean;
}

export interface ProductDestinationGroup extends ArticleGroup {
  corte: string;
  mercado: string;
  pais_destino: string;
  temperatura: string;
  presentacion: string;
  vida_util: number;
}

export interface PackagingGroup extends ArticleGroup {
  envase_primario: string;
  envase_exterior: string | null;
  tipo_peso: string;
  peso_promedio_kg: number | null;
}

export interface ArticleDocument {
  identificacion: IdentificationGroup;
  producto_destino: ProductDestinationGroup;
  codigos_asociaciones: ArticleGroup;
  envase_pesaje: PackagingGroup;
  etiquetado: ArticleGroup;
  fechas_operacion: ArticleGroup;
  comercial_operativo: ArticleGroup;
  calidad_seguridad: ArticleGroup;
  metadata: ArticleGroup;
  ficha_id?: string;
}

export interface FilterCriterion {
  field: string;
  operator: FilterOperator;
  value?: unknown;
}

export interface SortCriterion {
  field: string;
  direction: SortDirection;
}

export interface SearchRequest {
  filters?: FilterCriterion[];
  sort?: SortCriterion[];
  page?: number;
  page_size?: number;
}
