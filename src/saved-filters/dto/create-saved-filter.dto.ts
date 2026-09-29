import { Type } from 'class-transformer';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsOptional, IsString, MaxLength, ValidateNested } from 'class-validator';
import { SearchArticlesDto } from '../../articles/dto/search-articles.dto';

export class CreateSavedFilterDto {
  @ApiProperty({ example: 'China congelados' })
  @IsString()
  @MaxLength(100)
  name!: string;
  @ApiPropertyOptional({ example: 'Productos congelados destinados a China' })
  @IsOptional()
  @IsString()
  @MaxLength(500)
  description?: string;
  @ApiProperty({ type: SearchArticlesDto })
  @ValidateNested()
  @Type(() => SearchArticlesDto)
  search!: SearchArticlesDto;
}
