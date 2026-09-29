import { HttpStatus, Injectable } from '@nestjs/common';
import { ApiError } from '../common/errors/api-error';
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
        'ARTICLE_NOT_FOUND',
        `Article ${codigo} was not found`,
        HttpStatus.NOT_FOUND,
      );
    return toDocument(article, article.technicalSheet?.fichaId);
  }

  async allDocuments(): Promise<ArticleDocument[]> {
    const articles = await this.prisma.article.findMany({ include: { technicalSheet: true } });
    return articles.map((article) => toDocument(article, article.technicalSheet?.fichaId));
  }

  async search(request: SearchRequest): Promise<object> {
    const filters = request.filters ?? [];
    const sort = request.sort ?? [];
    const page = request.page ?? 1;
    const pageSize = request.page_size ?? 20;
    if (
      !Number.isInteger(page) ||
      page < 1 ||
      !Number.isInteger(pageSize) ||
      pageSize < 1 ||
      pageSize > 50
    ) {
      throw new ApiError(
        'INVALID_PAGINATION',
        'page must be >= 1 and page_size between 1 and 50',
        HttpStatus.BAD_REQUEST,
      );
    }
    filters.forEach((filter) => this.validateFilter(filter));
    sort.forEach((item) => this.validateSort(item));
    let documents = await this.allDocuments();
    documents = documents.filter((document) =>
      filters.every((filter) => this.matches(document, filter)),
    );
    documents.sort((a, b) => this.compareDocuments(a, b, sort));
    const totalItems = documents.length;
    const start = (page - 1) * pageSize;
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

  async compare(codes: string[]): Promise<object> {
    if (codes.length < 2 || codes.length > 10 || new Set(codes).size !== codes.length) {
      throw new ApiError(
        'INVALID_COMPARISON',
        'Provide between 2 and 10 unique article codes',
        HttpStatus.BAD_REQUEST,
      );
    }
    const documents = await Promise.all(codes.map((code) => this.findOne(code)));
    const fields = COMPARABLE_FIELDS.map((metadata) => {
      const values = Object.fromEntries(
        codes.map((code, index) => [code, getPath(documents[index], metadata.path)]),
      );
      const distinct = new Set(Object.values(values).map((value) => JSON.stringify(value)));
      return { field: metadata.path, values, different: distinct.size > 1 };
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
        'INVALID_FILTER_FIELD',
        `Field ${filter.field} is not filterable`,
        HttpStatus.BAD_REQUEST,
      );
    if (!metadata.operators.includes(filter.operator as never)) {
      throw new ApiError(
        'INVALID_FILTER_OPERATOR',
        `Operator ${filter.operator} is not allowed for ${filter.field}`,
        HttpStatus.BAD_REQUEST,
      );
    }
    this.validateValue(metadata, filter.operator, filter.value, 'INVALID_FILTER_VALUE');
  }

  validateCriterion(field: string, value: unknown): void {
    const metadata = FILTERABLE_FIELDS.get(field);
    if (!metadata?.can_be_required)
      throw new ApiError(
        'INVALID_REQUIRED_CRITERION',
        `Field ${field} cannot be required`,
        HttpStatus.BAD_REQUEST,
      );
    this.validateValue(metadata, 'eq', value, 'INVALID_REQUIRED_CRITERION');
  }

  private validateValue(
    metadata: FieldMetadata,
    operator: string,
    value: unknown,
    code: string,
  ): void {
    if (operator === 'is_null') {
      if (value !== undefined && typeof value !== 'boolean')
        throw new ApiError(
          code,
          'is_null value must be omitted or boolean',
          HttpStatus.BAD_REQUEST,
        );
      return;
    }
    const values = operator === 'in' || operator === 'between' ? value : [value];
    if (
      !Array.isArray(values) ||
      (operator === 'between' && values.length !== 2) ||
      (operator === 'in' && values.length === 0)
    ) {
      throw new ApiError(
        code,
        `${operator} requires an array${operator === 'between' ? ' of two values' : ''}`,
        HttpStatus.BAD_REQUEST,
      );
    }
    for (const item of values) {
      const expected = metadata.type === 'date' ? 'string' : metadata.type;
      if (
        typeof item !== expected ||
        (metadata.type === 'date' && Number.isNaN(Date.parse(String(item))))
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
        'INVALID_FILTER_FIELD',
        `Field ${sort.field} cannot be sorted`,
        HttpStatus.BAD_REQUEST,
      );
    if (!['asc', 'desc'].includes(sort.direction))
      throw new ApiError(
        'INVALID_FILTER_VALUE',
        'Sort direction must be asc or desc',
        HttpStatus.BAD_REQUEST,
      );
  }

  private matches(document: ArticleDocument, filter: FilterCriterion): boolean {
    const candidate = getPath(document, filter.field);
    const value = filter.value;
    switch (filter.operator) {
      case 'eq':
        return candidate === value;
      case 'neq':
        return candidate !== value;
      case 'in':
        return (value as unknown[]).includes(candidate);
      case 'contains':
        return (
          typeof candidate === 'string' &&
          candidate.toLowerCase().includes(String(value).toLowerCase())
        );
      case 'gte':
        return (
          this.orderable(candidate) !== null && this.orderable(candidate)! >= this.orderable(value)!
        );
      case 'lte':
        return (
          this.orderable(candidate) !== null && this.orderable(candidate)! <= this.orderable(value)!
        );
      case 'between': {
        const [min, max] = value as unknown[];
        const item = this.orderable(candidate);
        return item !== null && item >= this.orderable(min)! && item <= this.orderable(max)!;
      }
      case 'is_null':
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
      : [{ field: 'identificacion.codigo', direction: 'asc' as const }];
    for (const sort of effective) {
      const left = getPath(a, sort.field);
      const right = getPath(b, sort.field);
      const result =
        left === right ? 0 : left === null ? -1 : right === null ? 1 : left! < right! ? -1 : 1;
      if (result) return sort.direction === 'asc' ? result : -result;
    }
    return 0;
  }

  private summary(article: ArticleDocument): object {
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
