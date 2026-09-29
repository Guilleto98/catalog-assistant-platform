import { Type } from 'class-transformer';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsArray, IsIn, IsInt, IsOptional, IsString, ValidateNested } from 'class-validator';

export class FilterDto {
  @ApiProperty({ example: 'producto_destino.mercado' })
  @IsString()
  field!: string;
  @ApiProperty({ enum: ['eq', 'neq', 'in', 'contains', 'gte', 'lte', 'between', 'is_null'] })
  @IsString()
  operator!: string;
  @ApiPropertyOptional({
    example: 'CHINA',
    description: 'Omitir para is_null; array para in/between',
  })
  @IsOptional()
  value?: unknown;
}

export class SortDto {
  @ApiProperty({ example: 'identificacion.codigo' })
  @IsString()
  field!: string;
  @ApiProperty({ enum: ['asc', 'desc'] })
  @IsIn(['asc', 'desc'])
  direction!: 'asc' | 'desc';
}

export class SearchArticlesDto {
  @ApiPropertyOptional({ type: [FilterDto] })
  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => FilterDto)
  filters: FilterDto[] = [];

  @ApiPropertyOptional({ type: [SortDto] })
  @IsOptional()
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => SortDto)
  sort: SortDto[] = [];

  @ApiPropertyOptional({ default: 1, minimum: 1 })
  @IsOptional()
  @IsInt()
  page = 1;
  @ApiPropertyOptional({ default: 20, minimum: 1, maximum: 50 })
  @IsOptional()
  @IsInt()
  page_size = 20;
}
