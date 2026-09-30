import { HttpStatus, Injectable } from '@nestjs/common';
import { ApiError } from '../common/errors/api-error';
import {
  API_ERROR_CODES,
  COMPARISON_FIELD_POLICY,
  COMPARISON_POLICY,
  COMPARISON_RESULT,
  FILTER_OPERATORS,
  FILTER_VALUE_POLICY,
  FIELD_TYPES,
  PAGINATION_POLICY,
  SORT_DIRECTIONS,
  type ApiErrorCode,
  type FilterOperator,
} from '../common/constants/api.constants';
import {
  COMPARABLE_FIELDS,
  FILTERABLE_FIELDS,
  type FieldMetadata,
} from '../common/metadata/field-metadata';
import type {
  ArticleDocument,
  FilterCriterion,
  SearchRequest,
  SortCriterion,
} from '../common/types/article.types';
import type {
  ArticleSummary,
  CompareArticlesResponse,
  SearchArticlesResponse,
} from '../common/types/api-responses';
import { PrismaService } from '../database/prisma.service';
import { getPath, toDocument } from './article.mapper';

@Injectable()
export class ArticlesService {
  constructor(private readonly prisma: PrismaService) {}

  async count(): Promise<number> {
    return this.prisma.article.count();
  }

  async findOne(codigo: string): Promise<ArticleDocument> {
    const article = await this.prisma.article.findUnique({
      where: { codigo },
      include: { technicalSheet: true },
    });
    if (!article)
      throw new ApiError(
        API_ERROR_CODES.ARTICLE_NOT_FOUND,
        `Article ${codigo} was not found`,
        HttpStatus.NOT_FOUND,
      );
    return toDocument(article, article.technicalSheet?.fichaId);
  }

  async allDocuments(): Promise<ArticleDocument[]> {
    // This intentionally loads the full catalog for the bounded demo dataset (50 articles).
    // Move filtering, sorting, and pagination into the repository before growing the dataset.
    const articles = await this.prisma.article.findMany({ include: { technicalSheet: true } });
    return articles.map((article) => toDocument(article, article.technicalSheet?.fichaId));
  }

  async search(request: SearchRequest): Promise<SearchArticlesResponse> {
    this.validateSearchRequest(request);
    const filters = request.filters ?? [];
    const sort = request.sort ?? [];
    const page = request.page ?? PAGINATION_POLICY.DEFAULT_PAGE;
    const pageSize = request.page_size ?? PAGINATION_POLICY.DEFAULT_PAGE_SIZE;

    let documents = await this.allDocuments();
    documents = documents.filter((document) =>
      filters.every((filter) => this.matches(document, filter)),
    );
    documents.sort((a, b) => this.compareDocuments(a, b, sort));
    const totalItems = documents.length;
    const start = (page - PAGINATION_POLICY.PAGE_INDEX_ORIGIN) * pageSize;
    return {
      items: documents.slice(start, start + pageSize).map((article) => this.summary(article)),
      pagination: {
        page,
        page_size: pageSize,
        total_items: totalItems,
        total_pages: Math.ceil(totalItems / pageSize),
      },
      applied_filters: filters,
      applied_sort: sort,
    };
  }

  validateSearchRequest(request: SearchRequest): void {
    const filters = request.filters ?? [];
    const sort = request.sort ?? [];
    const page = request.page ?? PAGINATION_POLICY.DEFAULT_PAGE;
    const pageSize = request.page_size ?? PAGINATION_POLICY.DEFAULT_PAGE_SIZE;
    if (
      !Number.isInteger(page) ||
      page < PAGINATION_POLICY.MIN_PAGE ||
      !Number.isInteger(pageSize) ||
      pageSize < PAGINATION_POLICY.MIN_PAGE_SIZE ||
      pageSize > PAGINATION_POLICY.MAX_PAGE_SIZE
    ) {
      throw new ApiError(
        API_ERROR_CODES.INVALID_PAGINATION,
        `page must be >= ${PAGINATION_POLICY.MIN_PAGE} and page_size between ${PAGINATION_POLICY.MIN_PAGE_SIZE} and ${PAGINATION_POLICY.MAX_PAGE_SIZE}`,
        HttpStatus.BAD_REQUEST,
      );
    }
    filters.forEach((filter) => this.validateFilter(filter));
    sort.forEach((item) => this.validateSort(item));
  }

  async compare(codes: string[]): Promise<CompareArticlesResponse> {
    if (
      codes.length < COMPARISON_POLICY.MIN_ARTICLES ||
      codes.length > COMPARISON_POLICY.MAX_ARTICLES ||
      new Set(codes).size !== codes.length
    ) {
      throw new ApiError(
        API_ERROR_CODES.INVALID_COMPARISON,
        `Provide between ${COMPARISON_POLICY.MIN_ARTICLES} and ${COMPARISON_POLICY.MAX_ARTICLES} unique article codes`,
        HttpStatus.BAD_REQUEST,
      );
    }
    const documents = await Promise.all(codes.map((code) => this.findOne(code)));
    const fields = COMPARABLE_FIELDS.map((metadata) => {
      const values = Object.fromEntries(
        codes.map((code, index) => [code, getPath(documents[index], metadata.path)]),
      );
      const distinct = new Set(Object.values(values).map((value) => JSON.stringify(value)));
      return {
        field: metadata.path,
        values,
        different: distinct.size >= COMPARISON_FIELD_POLICY.MIN_DISTINCT_VALUES_TO_DIFFER,
      };
    });
    return {
      compared_codes: codes,
      fields,
      different_fields_count: fields.filter((field) => field.different).length,
      equal_fields_count: fields.filter((field) => !field.different).length,
    };
  }

  validateFilter(filter: FilterCriterion): void {
    const metadata = FILTERABLE_FIELDS.get(filter.field);
    if (!metadata)
      throw new ApiError(
        API_ERROR_CODES.INVALID_FILTER_FIELD,
        `Field ${filter.field} is not filterable`,
        HttpStatus.BAD_REQUEST,
      );
    if (!metadata.operators.includes(filter.operator)) {
      throw new ApiError(
        API_ERROR_CODES.INVALID_FILTER_OPERATOR,
        `Operator ${filter.operator} is not allowed for ${filter.field}`,
        HttpStatus.BAD_REQUEST,
      );
    }
    this.validateValue(
      metadata,
      filter.operator,
      filter.value,
      API_ERROR_CODES.INVALID_FILTER_VALUE,
    );
  }

  validateCriterion(field: string, value: unknown): void {
    const metadata = FILTERABLE_FIELDS.get(field);
    if (!metadata?.can_be_required)
      throw new ApiError(
        API_ERROR_CODES.INVALID_REQUIRED_CRITERION,
        `Field ${field} cannot be required`,
        HttpStatus.BAD_REQUEST,
      );
    this.validateValue(
      metadata,
      FILTER_OPERATORS.EQUALS,
      value,
      API_ERROR_CODES.INVALID_REQUIRED_CRITERION,
    );
  }

  private validateValue(
    metadata: FieldMetadata,
    operator: FilterOperator,
    value: unknown,
    code: ApiErrorCode,
  ): void {
    if (operator === FILTER_OPERATORS.IS_NULL) {
      if (value !== undefined && typeof value !== 'boolean')
        throw new ApiError(
          code,
          'is_null value must be omitted or boolean',
          HttpStatus.BAD_REQUEST,
        );
      return;
    }
    const values =
      operator === FILTER_OPERATORS.IN || operator === FILTER_OPERATORS.BETWEEN ? value : [value];
    if (
      !Array.isArray(values) ||
      (operator === FILTER_OPERATORS.BETWEEN &&
        values.length !== FILTER_VALUE_POLICY.BETWEEN_VALUE_COUNT) ||
      (operator === FILTER_OPERATORS.IN && values.length < FILTER_VALUE_POLICY.MIN_IN_VALUES)
    ) {
      throw new ApiError(
        code,
        `${operator} requires an array${operator === FILTER_OPERATORS.BETWEEN ? ` of ${FILTER_VALUE_POLICY.BETWEEN_VALUE_COUNT} values` : ''}`,
        HttpStatus.BAD_REQUEST,
      );
    }
    for (const item of values) {
      const expected = metadata.type === FIELD_TYPES.DATE ? FIELD_TYPES.STRING : metadata.type;
      if (
        typeof item !== expected ||
        (metadata.type === FIELD_TYPES.DATE && Number.isNaN(Date.parse(String(item))))
      ) {
        throw new ApiError(code, `Invalid value type for ${metadata.path}`, HttpStatus.BAD_REQUEST);
      }
      if (metadata.allowed_values && !metadata.allowed_values.includes(item as never)) {
        throw new ApiError(
          code,
          `Value ${String(item)} is not allowed for ${metadata.path}`,
          HttpStatus.BAD_REQUEST,
        );
      }
    }
  }

  private validateSort(sort: SortCriterion): void {
    if (!FILTERABLE_FIELDS.has(sort.field))
      throw new ApiError(
        API_ERROR_CODES.INVALID_FILTER_FIELD,
        `Field ${sort.field} cannot be sorted`,
        HttpStatus.BAD_REQUEST,
      );
    if (!Object.values(SORT_DIRECTIONS).includes(sort.direction))
      throw new ApiError(
        API_ERROR_CODES.INVALID_FILTER_VALUE,
        `Sort direction must be ${Object.values(SORT_DIRECTIONS).join(' or ')}`,
        HttpStatus.BAD_REQUEST,
      );
  }

  private matches(document: ArticleDocument, filter: FilterCriterion): boolean {
    const candidate = getPath(document, filter.field);
    const value = filter.value;
    switch (filter.operator) {
      case FILTER_OPERATORS.EQUALS:
        return candidate === value;
      case FILTER_OPERATORS.NOT_EQUALS:
        return candidate !== value;
      case FILTER_OPERATORS.IN:
        return (value as unknown[]).includes(candidate);
      case FILTER_OPERATORS.CONTAINS:
        return (
          typeof candidate === 'string' &&
          candidate.toLowerCase().includes(String(value).toLowerCase())
        );
      case FILTER_OPERATORS.GREATER_THAN_OR_EQUAL:
        return (
          this.orderable(candidate) !== null && this.orderable(candidate)! >= this.orderable(value)!
        );
      case FILTER_OPERATORS.LESS_THAN_OR_EQUAL:
        return (
          this.orderable(candidate) !== null && this.orderable(candidate)! <= this.orderable(value)!
        );
      case FILTER_OPERATORS.BETWEEN: {
        const [min, max] = value as unknown[];
        const item = this.orderable(candidate);
        return item !== null && item >= this.orderable(min)! && item <= this.orderable(max)!;
      }
      case FILTER_OPERATORS.IS_NULL:
        return value === false
          ? candidate !== null && candidate !== undefined
          : candidate === null || candidate === undefined;
      default:
        return false;
    }
  }

  private orderable(value: unknown): number | string | null {
    if (typeof value === 'number') return value;
    if (typeof value === 'string') return value;
    return null;
  }

  private compareDocuments(a: ArticleDocument, b: ArticleDocument, sorts: SortCriterion[]): number {
    const effective = sorts.length
      ? sorts
      : [{ field: 'identificacion.codigo', direction: SORT_DIRECTIONS.ASCENDING }];
    for (const sort of effective) {
      const left = getPath(a, sort.field);
      const right = getPath(b, sort.field);
      const result =
        left === right
          ? COMPARISON_RESULT.EQUAL
          : left === null
            ? COMPARISON_RESULT.LESS_THAN
            : right === null
              ? COMPARISON_RESULT.GREATER_THAN
              : left! < right!
                ? COMPARISON_RESULT.LESS_THAN
                : COMPARISON_RESULT.GREATER_THAN;
      if (result) return sort.direction === SORT_DIRECTIONS.ASCENDING ? result : -result;
    }
    return COMPARISON_RESULT.EQUAL;
  }

  private summary(article: ArticleDocument): ArticleSummary {
    const id = article.identificacion;
    const product = article.producto_destino;
    const pack = article.envase_pesaje;
    return {
      codigo: id.codigo,
      nombre: id.nombre,
      corte: product.corte,
      especie: id.especie,
      mercado: product.mercado,
      pais_destino: product.pais_destino,
      temperatura: product.temperatura,
      presentacion: product.presentacion,
      envase_primario: pack.envase_primario,
      envase_exterior: pack.envase_exterior,
      tipo_peso: pack.tipo_peso,
      peso_promedio_kg: pack.peso_promedio_kg,
      activo: id.activo,
      ficha_id: article.ficha_id,
    };
  }
}
