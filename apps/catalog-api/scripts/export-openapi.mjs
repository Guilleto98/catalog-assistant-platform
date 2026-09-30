import { writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { NestFactory } = require('@nestjs/core');
const { SwaggerModule } = require('@nestjs/swagger');
const { AppModule } = require('../dist/app.module.js');
const { API_CONFIGURATION } = require('../dist/common/constants/api.constants.js');
const { createOpenApiConfig } = require('../dist/common/openapi.js');

const app = await NestFactory.create(AppModule, { logger: false });
try {
  app.setGlobalPrefix(API_CONFIGURATION.GLOBAL_PREFIX);
  const document = SwaggerModule.createDocument(app, createOpenApiConfig());
  await writeFile(
    new URL('../docs/openapi.json', import.meta.url),
    `${JSON.stringify(document, null, 2)}\n`,
  );
  process.stdout.write(`OpenAPI exported with ${Object.keys(document.paths).length} paths.\n`);
} finally {
  await app.close();
}
