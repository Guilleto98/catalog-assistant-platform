import { Module } from '@nestjs/common';
import { ArticlesModule } from '../articles/articles.module';
import { HealthController } from './health.controller';
@Module({ imports: [ArticlesModule], controllers: [HealthController] })
export class HealthModule {}
