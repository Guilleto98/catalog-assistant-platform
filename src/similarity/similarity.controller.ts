import { Body, Controller, Post } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { SimilarArticlesDto } from './dto/similar-articles.dto';
import { SimilarityService } from './similarity.service';

@ApiTags('articles')
@Controller('articles')
export class SimilarityController {
  constructor(private readonly similarity: SimilarityService) {}
  @Post('similar')
  @ApiOperation({ summary: 'Calcula similitud y aptitud de forma determinística' })
  similar(@Body() dto: SimilarArticlesDto): Promise<object> {
    return this.similarity.findSimilar(dto);
  }
}
