import { IsInt, IsObject, IsOptional, IsString, ValidateIf } from 'class-validator';
import { ApiPropertyOptional } from '@nestjs/swagger';

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

  @ApiPropertyOptional({ default: 10, minimum: 1, maximum: 10 })
  @IsOptional()
  @IsInt()
  limit = 10;
}
