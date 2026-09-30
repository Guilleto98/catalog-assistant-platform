import { DocumentBuilder, type OpenAPIObject } from '@nestjs/swagger';
import { API_CONFIGURATION } from './constants/api.constants';

export function createOpenApiConfig(): Omit<OpenAPIObject, 'paths'> {
  return new DocumentBuilder()
    .setTitle('Uruguay Meat Catalog API')
    .setDescription('API educativa: datos 100 % sintéticos, no oficiales')
    .setVersion(API_CONFIGURATION.OPENAPI_VERSION)
    .addApiKey(
      {
        type: 'apiKey',
        in: 'header',
        name: 'X-Demo-User-Id',
        description: 'Simulación local; no autentica',
      },
      'demo-user',
    )
    .build();
}
