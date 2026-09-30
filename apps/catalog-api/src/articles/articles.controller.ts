import { Body, Controller, Get, Param, Post } from '@nestjs/common';
import { ApiCreatedResponse, ApiOkResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import { ArticlesService } from './articles.service';
import { CompareArticlesDto } from './dto/compare-articles.dto';
import { SearchArticlesDto } from './dto/search-articles.dto';
import type { ArticleDocument } from '../common/types/article.types';
import { COMPARISON_POLICY } from '../common/constants/api.constants';
import type {
  CompareArticlesResponse,
  SearchArticlesResponse,
} from '../common/types/api-responses';
import {
  ArticleDocumentResponseDto,
  CompareArticlesResponseDto,
  SearchArticlesResponseDto,
} from '../common/dto/api-responses.dto';

@ApiTags('articles')
@Controller('articles')
export class ArticlesController {
  constructor(private readonly articles: ArticlesService) {}

  @Post('search')
  @ApiOperation({ summary: 'Busca artículos con filtros determinísticos' })
  @ApiCreatedResponse({ type: SearchArticlesResponseDto })
  search(@Body() dto: SearchArticlesDto): Promise<SearchArticlesResponse> {
    return this.articles.search(dto);
  }

  @Post('compare')
  @ApiOperation({
    summary: `Compara atributos de ${COMPARISON_POLICY.MIN_ARTICLES} a ${COMPARISON_POLICY.MAX_ARTICLES} artículos`,
  })
  @ApiCreatedResponse({ type: CompareArticlesResponseDto })
  compare(@Body() dto: CompareArticlesDto): Promise<CompareArticlesResponse> {
    return this.articles.compare(dto.codes);
  }

  @Get(':codigo')
  @ApiOperation({ summary: 'Obtiene un artículo completo' })
  @ApiOkResponse({ type: ArticleDocumentResponseDto })
  findOne(@Param('codigo') codigo: string): Promise<ArticleDocument> {
    return this.articles.findOne(codigo);
  }
}
