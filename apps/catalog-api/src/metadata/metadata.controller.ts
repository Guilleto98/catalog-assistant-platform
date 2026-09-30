import { Controller, Get } from '@nestjs/common';
import { ApiOkResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import { FIELD_METADATA } from '../common/metadata/field-metadata';
import type { FilterableFieldsResponse } from '../common/types/api-responses';
import { FilterableFieldsResponseDto } from '../common/dto/api-responses.dto';

@ApiTags('metadata')
@Controller('metadata')
export class MetadataController {
  @Get('filterable-fields')
  @ApiOperation({ summary: 'Publica el contrato central de filtros' })
  @ApiOkResponse({ type: FilterableFieldsResponseDto })
  fields(): FilterableFieldsResponse {
    return {
      fields: FIELD_METADATA.filter((field) => field.filterable).map(
        ({
          path,
          type,
          nullable,
          unit,
          operators,
          allowed_values,
          used_for_similarity,
          can_be_required,
        }) => ({
          path,
          type,
          nullable,
          unit,
          operators,
          used_for_similarity,
          can_be_required,
          ...(allowed_values ? { allowed_values } : {}),
        }),
      ),
    };
  }
}
