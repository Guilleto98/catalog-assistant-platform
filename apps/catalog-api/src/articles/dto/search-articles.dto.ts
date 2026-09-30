import { Type } from 'class-transformer';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import {
  IsArray,
  IsIn,
  IsInt,
  IsOptional,
  IsString,
  Max,
  Min,
  ValidateNested,
} from 'class-validator';
import {
  FILTER_OPERATOR_VALUES,
  PAGINATION_POLICY,
  SORT_DIRECTION_VALUES,
  type FilterOperator,
  type SortDirection,
} from '../../common/constants/api.constants';

export class FilterDto {
  @ApiProperty({ example: 'producto_destino.mercado' })
  @IsString()
  field!: string;
  @ApiProperty({ enum: FILTER_OPERATOR_VALUES })
  @IsIn(FILTER_OPERATOR_VALUES)
  operator!: FilterOperator;
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
  @ApiProperty({ enum: SORT_DIRECTION_VALUES })
  @IsIn(SORT_DIRECTION_VALUES)
  direction!: SortDirection;
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

  @ApiPropertyOptional({
    default: PAGINATION_POLICY.DEFAULT_PAGE,
    minimum: PAGINATION_POLICY.MIN_PAGE,
  })
  @IsOptional()
  @IsInt()
  @Min(PAGINATION_POLICY.MIN_PAGE)
  page = PAGINATION_POLICY.DEFAULT_PAGE;
  @ApiPropertyOptional({
    default: PAGINATION_POLICY.DEFAULT_PAGE_SIZE,
    minimum: PAGINATION_POLICY.MIN_PAGE_SIZE,
    maximum: PAGINATION_POLICY.MAX_PAGE_SIZE,
  })
  @IsOptional()
  @IsInt()
  @Min(PAGINATION_POLICY.MIN_PAGE_SIZE)
  @Max(PAGINATION_POLICY.MAX_PAGE_SIZE)
  page_size = PAGINATION_POLICY.DEFAULT_PAGE_SIZE;
}
