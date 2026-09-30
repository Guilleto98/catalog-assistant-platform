import { IsInt, IsObject, IsOptional, IsString, Max, Min, ValidateIf } from 'class-validator';
import { ApiPropertyOptional } from '@nestjs/swagger';
import { SIMILARITY_POLICY } from '../../common/constants/api.constants';

export class SimilarArticlesDto {
  @ApiPropertyOptional({
    example: '900001',
    description: 'Usar reference_code o features, nunca ambos',
  })
  @ValidateIf((object: SimilarArticlesDto) => object.features === undefined)
  @IsString()
  reference_code?: string;

  @ApiPropertyOptional({ example: { 'producto_destino.corte': 'BIFE_ANCHO' } })
  @ValidateIf((object: SimilarArticlesDto) => object.reference_code === undefined)
  @IsObject()
  features?: Record<string, unknown>;

  @ApiPropertyOptional({ example: { 'producto_destino.mercado': 'CHINA' } })
  @IsOptional()
  @IsObject()
  required?: Record<string, unknown>;

  @ApiPropertyOptional({
    default: SIMILARITY_POLICY.DEFAULT_LIMIT,
    minimum: SIMILARITY_POLICY.MIN_LIMIT,
    maximum: SIMILARITY_POLICY.MAX_LIMIT,
  })
  @IsOptional()
  @IsInt()
  @Min(SIMILARITY_POLICY.MIN_LIMIT)
  @Max(SIMILARITY_POLICY.MAX_LIMIT)
  limit = SIMILARITY_POLICY.DEFAULT_LIMIT;
}
