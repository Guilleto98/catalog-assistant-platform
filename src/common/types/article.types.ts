export type JsonScalar = string | number | boolean | null;
export type ArticleGroup = Record<string, JsonScalar>;

export interface ArticleDocument {
  identificacion: ArticleGroup;
  producto_destino: ArticleGroup;
  codigos_asociaciones: ArticleGroup;
  envase_pesaje: ArticleGroup;
  etiquetado: ArticleGroup;
  fechas_operacion: ArticleGroup;
  comercial_operativo: ArticleGroup;
  calidad_seguridad: ArticleGroup;
  metadata: ArticleGroup;
  ficha_id?: string;
}

export interface FilterCriterion {
  field: string;
  operator: string;
  value?: unknown;
}

export interface SortCriterion {
  field: string;
  direction: 'asc' | 'desc';
}

export interface SearchRequest {
  filters?: FilterCriterion[];
  sort?: SortCriterion[];
  page?: number;
  page_size?: number;
}
