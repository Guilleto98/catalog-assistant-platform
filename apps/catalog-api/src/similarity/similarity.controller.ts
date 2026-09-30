import { Body, Controller, Post } from '@nestjs/common';
import { ApiCreatedResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import { SimilarArticlesDto } from './dto/similar-articles.dto';
import { SimilarityService } from './similarity.service';
import type { FindSimilarArticlesResponse } from '../common/types/api-responses';
import { FindSimilarArticlesResponseDto } from '../common/dto/api-responses.dto';

@ApiTags('articles')
@Controller('articles')
export class SimilarityController {
  constructor(private readonly similarity: SimilarityService) {}
  @Post('similar')
  @ApiOperation({ summary: 'Calcula similitud y aptitud de forma determinística' })
  @ApiCreatedResponse({ type: FindSimilarArticlesResponseDto })
  similar(@Body() dto: SimilarArticlesDto): Promise<FindSimilarArticlesResponse> {
    return this.similarity.findSimilar(dto);
  }
}
