import { Module } from '@nestjs/common';
import { ArticlesModule } from './articles/articles.module';
import { DatabaseModule } from './database/database.module';
import { HealthModule } from './health/health.module';
import { MetadataModule } from './metadata/metadata.module';
import { SavedFiltersModule } from './saved-filters/saved-filters.module';
import { SimilarityModule } from './similarity/similarity.module';
import { TechnicalSheetsModule } from './technical-sheets/technical-sheets.module';

@Module({
  imports: [
    DatabaseModule,
    ArticlesModule,
    SimilarityModule,
    TechnicalSheetsModule,
    SavedFiltersModule,
    MetadataModule,
    HealthModule,
  ],
})
export class AppModule {}
