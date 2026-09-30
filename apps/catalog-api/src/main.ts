import 'dotenv/config';
import 'reflect-metadata';
import { ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { SwaggerModule } from '@nestjs/swagger';
import { AppModule } from './app.module';
import { ApiExceptionFilter } from './common/errors/api-exception.filter';
import { API_CONFIGURATION } from './common/constants/api.constants';
import { createOpenApiConfig } from './common/openapi';

export async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule);
  app.setGlobalPrefix(API_CONFIGURATION.GLOBAL_PREFIX);
  app.useGlobalPipes(
    new ValidationPipe({ transform: true, whitelist: true, forbidNonWhitelisted: true }),
  );
  app.useGlobalFilters(new ApiExceptionFilter());
  SwaggerModule.setup('api/docs', app, SwaggerModule.createDocument(app, createOpenApiConfig()));
  await app.listen(Number(process.env.PORT ?? API_CONFIGURATION.DEFAULT_PORT));
}

if (require.main === module) void bootstrap();
