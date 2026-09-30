import { Type } from 'class-transformer';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsOptional, IsString, MaxLength, ValidateNested } from 'class-validator';
import { SAVED_FILTER_POLICY } from '../../common/constants/api.constants';
import { SearchArticlesDto } from '../../articles/dto/search-articles.dto';

export class CreateSavedFilterDto {
  @ApiProperty({ example: 'China congelados' })
  @IsString()
  @MaxLength(SAVED_FILTER_POLICY.MAX_NAME_LENGTH)
  name!: string;
  @ApiPropertyOptional({ example: 'Productos congelados destinados a China' })
  @IsOptional()
  @IsString()
  @MaxLength(SAVED_FILTER_POLICY.MAX_DESCRIPTION_LENGTH)
  description?: string;
  @ApiProperty({ type: SearchArticlesDto })
  @ValidateNested()
  @Type(() => SearchArticlesDto)
  search!: SearchArticlesDto;
}
