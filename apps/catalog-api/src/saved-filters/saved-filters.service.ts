import { randomUUID } from 'node:crypto';
import { HttpStatus, Injectable } from '@nestjs/common';
import type { Prisma, SavedFilter } from '@prisma/client';
import {
  FILTER_OPERATOR_VALUES,
  SORT_DIRECTION_VALUES,
  API_ERROR_CODES,
} from '../common/constants/api.constants';
import { ArticlesService } from '../articles/articles.service';
import { ApiError } from '../common/errors/api-error';
import type { FilterCriterion, SearchRequest, SortCriterion } from '../common/types/article.types';
import type { SavedFilterResponse, SearchArticlesResponse } from '../common/types/api-responses';
import { PrismaService } from '../database/prisma.service';
import type { CreateSavedFilterDto } from './dto/create-saved-filter.dto';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isFilterCriterion(value: unknown): value is FilterCriterion {
  return (
    isRecord(value) &&
    typeof value.field === 'string' &&
    typeof value.operator === 'string' &&
    FILTER_OPERATOR_VALUES.includes(value.operator as (typeof FILTER_OPERATOR_VALUES)[number])
  );
}

function isSortCriterion(value: unknown): value is SortCriterion {
  return (
    isRecord(value) &&
    typeof value.field === 'string' &&
    typeof value.direction === 'string' &&
    SORT_DIRECTION_VALUES.includes(value.direction as (typeof SORT_DIRECTION_VALUES)[number])
  );
}

function parseSavedSearch(value: Prisma.JsonValue): SearchRequest {
  if (!isRecord(value)) throw invalidStoredFilter();
  const rawFilters = value.filters ?? [];
  const rawSort = value.sort ?? [];
  if (!Array.isArray(rawFilters) || !Array.isArray(rawSort)) throw invalidStoredFilter();
  const filters = rawFilters.map((filter) => {
    if (!isFilterCriterion(filter)) throw invalidStoredFilter();
    return filter;
  });
  const sort = rawSort.map((criterion) => {
    if (!isSortCriterion(criterion)) throw invalidStoredFilter();
    return criterion;
  });
  if (
    (value.page !== undefined && typeof value.page !== 'number') ||
    (value.page_size !== undefined && typeof value.page_size !== 'number')
  ) {
    throw invalidStoredFilter();
  }
  return {
    filters,
    sort,
    ...(typeof value.page === 'number' ? { page: value.page } : {}),
    ...(typeof value.page_size === 'number' ? { page_size: value.page_size } : {}),
  };
}

function invalidStoredFilter(): ApiError {
  return new ApiError(
    API_ERROR_CODES.INVALID_STORED_FILTER,
    'The saved filter contains an invalid search request',
    HttpStatus.INTERNAL_SERVER_ERROR,
  );
}

@Injectable()
export class SavedFiltersService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly articles: ArticlesService,
  ) {}

  async requireUser(userId?: string): Promise<string> {
    if (!userId)
      throw new ApiError(
        API_ERROR_CODES.DEMO_USER_REQUIRED,
        'X-Demo-User-Id header is required',
        HttpStatus.BAD_REQUEST,
      );
    const user = await this.prisma.demoUser.findUnique({ where: { id: userId } });
    if (!user)
      throw new ApiError(
        API_ERROR_CODES.DEMO_USER_NOT_FOUND,
        `Demo user ${userId} was not found`,
        HttpStatus.NOT_FOUND,
      );
    return userId;
  }

  async create(
    userId: string | undefined,
    dto: CreateSavedFilterDto,
  ): Promise<SavedFilterResponse> {
    const ownerUserId = await this.requireUser(userId);
    this.articles.validateSearchRequest(dto.search);
    const now = new Date();
    return this.serialize(
      await this.prisma.savedFilter.create({
        data: {
          id: randomUUID(),
          ownerUserId,
          name: dto.name,
          description: dto.description,
          search: dto.search as unknown as Prisma.InputJsonValue,
          createdAt: now,
          updatedAt: now,
        },
      }),
    );
  }

  async list(userId?: string): Promise<SavedFilterResponse[]> {
    const ownerUserId = await this.requireUser(userId);
    return (
      await this.prisma.savedFilter.findMany({
        where: { ownerUserId },
        orderBy: { createdAt: 'asc' },
      })
    ).map((item) => this.serialize(item));
  }

  async get(userId: string | undefined, id: string): Promise<SavedFilter> {
    const ownerUserId = await this.requireUser(userId);
    const item = await this.prisma.savedFilter.findFirst({ where: { id, ownerUserId } });
    if (!item)
      throw new ApiError(
        API_ERROR_CODES.SAVED_FILTER_NOT_FOUND,
        `Saved filter ${id} was not found`,
        HttpStatus.NOT_FOUND,
      );
    return item;
  }

  async getSerialized(userId: string | undefined, id: string): Promise<SavedFilterResponse> {
    return this.serialize(await this.get(userId, id));
  }
  async execute(userId: string | undefined, id: string): Promise<SearchArticlesResponse> {
    const item = await this.get(userId, id);
    return this.articles.search(parseSavedSearch(item.search));
  }
  async remove(userId: string | undefined, id: string): Promise<void> {
    const item = await this.get(userId, id);
    await this.prisma.savedFilter.delete({ where: { id: item.id } });
  }

  private serialize(item: {
    id: string;
    ownerUserId: string;
    name: string;
    description: string | null;
    search: Prisma.JsonValue;
    createdAt: Date;
    updatedAt: Date;
  }): SavedFilterResponse {
    return {
      id: item.id,
      owner_user_id: item.ownerUserId,
      name: item.name,
      description: item.description,
      search: parseSavedSearch(item.search),
      created_at: item.createdAt.toISOString(),
      updated_at: item.updatedAt.toISOString(),
    };
  }
}
