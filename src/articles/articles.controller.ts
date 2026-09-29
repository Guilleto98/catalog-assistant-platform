import { Body, Controller, Get, Param, Post } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { ArticlesService } from './articles.service';
import { CompareArticlesDto } from './dto/compare-articles.dto';
import { SearchArticlesDto } from './dto/search-articles.dto';

@ApiTags('articles')
@Controller('articles')
export class ArticlesController {
  constructor(private readonly articles: ArticlesService) {}

  @Post('search')
  @ApiOperation({ summary: 'Busca artículos con filtros determinísticos' })
  search(@Body() dto: SearchArticlesDto): Promise<object> {
    return this.articles.search(dto);
  }

  @Post('compare')
  @ApiOperation({ summary: 'Compara atributos de 2 a 10 artículos' })
  compare(@Body() dto: CompareArticlesDto): Promise<object> {
    return this.articles.compare(dto.codes);
  }

  @Get(':codigo')
  @ApiOperation({ summary: 'Obtiene un artículo completo' })
  findOne(@Param('codigo') codigo: string): Promise<object> {
    return this.articles.findOne(codigo);
  }
}
