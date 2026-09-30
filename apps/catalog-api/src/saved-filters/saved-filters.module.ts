import { Module } from '@nestjs/common';
import { ArticlesModule } from '../articles/articles.module';
import { SavedFiltersController } from './saved-filters.controller';
import { SavedFiltersService } from './saved-filters.service';

@Module({
  imports: [ArticlesModule],
  controllers: [SavedFiltersController],
  providers: [SavedFiltersService],
})
export class SavedFiltersModule {}
