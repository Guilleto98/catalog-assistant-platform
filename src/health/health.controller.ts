import { Controller, Get } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { ArticlesService } from '../articles/articles.service';

@ApiTags('health')
@Controller('health')
export class HealthController {
  constructor(private readonly articles: ArticlesService) {}
  @Get()
  @ApiOperation({ summary: 'Estado y versión del dataset' })
  async health(): Promise<object> {
    return { status: 'ok', dataset_version: 'v1', articles: await this.articles.count() };
  }
}
