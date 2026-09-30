import { Module } from '@nestjs/common';
import { ArticlesModule } from '../articles/articles.module';
import { SimilarityController } from './similarity.controller';
import { SimilarityService } from './similarity.service';

@Module({
  imports: [ArticlesModule],
  controllers: [SimilarityController],
  providers: [SimilarityService],
})
export class SimilarityModule {}
