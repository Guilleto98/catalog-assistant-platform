import { randomUUID } from 'node:crypto';
import { HttpStatus, Injectable } from '@nestjs/common';
import type { Prisma, SavedFilter } from '@prisma/client';
import { ArticlesService } from '../articles/articles.service';
import { ApiError } from '../common/errors/api-error';
import type { SearchRequest } from '../common/types/article.types';
import { PrismaService } from '../database/prisma.service';
import type { CreateSavedFilterDto } from './dto/create-saved-filter.dto';

@Injectable()
export class SavedFiltersService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly articles: ArticlesService,
  ) {}

  async requireUser(userId?: string): Promise<string> {
    if (!userId)
      throw new ApiError(
        'DEMO_USER_REQUIRED',
        'X-Demo-User-Id header is required',
        HttpStatus.BAD_REQUEST,
      );
    const user = await this.prisma.demoUser.findUnique({ where: { id: userId } });
    if (!user)
      throw new ApiError(
        'DEMO_USER_NOT_FOUND',
        `Demo user ${userId} was not found`,
        HttpStatus.NOT_FOUND,
      );
    return userId;
  }

  async create(userId: string | undefined, dto: CreateSavedFilterDto): Promise<object> {
    const ownerUserId = await this.requireUser(userId);
    await this.articles.search(dto.search);
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

  async list(userId?: string): Promise<object[]> {
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
        'SAVED_FILTER_NOT_FOUND',
        `Saved filter ${id} was not found`,
        HttpStatus.NOT_FOUND,
      );
    return item;
  }

  async getSerialized(userId: string | undefined, id: string): Promise<object> {
    return this.serialize(await this.get(userId, id));
  }
  async execute(userId: string | undefined, id: string): Promise<object> {
    const item = await this.get(userId, id);
    return this.articles.search(item.search as unknown as SearchRequest);
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
  }): object {
    return {
      id: item.id,
      owner_user_id: item.ownerUserId,
      name: item.name,
      description: item.description,
      search: item.search,
      created_at: item.createdAt.toISOString(),
      updated_at: item.updatedAt.toISOString(),
    };
  }
}
