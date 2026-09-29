import { Controller, Get } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { FIELD_METADATA } from '../common/metadata/field-metadata';

@ApiTags('metadata')
@Controller('metadata')
export class MetadataController {
  @Get('filterable-fields')
  @ApiOperation({ summary: 'Publica el contrato central de filtros' })
  fields(): object {
    return {
      fields: FIELD_METADATA.filter((field) => field.filterable).map(
        ({ path, type, nullable, unit, operators, allowed_values }) => ({
          path,
          type,
          nullable,
          unit,
          operators,
          ...(allowed_values ? { allowed_values } : {}),
        }),
      ),
    };
  }
}
