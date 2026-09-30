import { Controller, Get } from '@nestjs/common';
import { ApiOkResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import { ArticlesService } from '../articles/articles.service';
import { API_CONFIGURATION } from '../common/constants/api.constants';
import type { HealthResponse } from '../common/types/api-responses';
import { HealthResponseDto } from '../common/dto/api-responses.dto';

@ApiTags('health')
@Controller('health')
export class HealthController {
  constructor(private readonly articles: ArticlesService) {}
  @Get()
  @ApiOperation({ summary: 'Estado y versión del dataset' })
  @ApiOkResponse({ type: HealthResponseDto })
  async health(): Promise<HealthResponse> {
    return {
      status: 'ok',
      dataset_version: API_CONFIGURATION.DATASET_VERSION,
      articles: await this.articles.count(),
    };
  }
}
