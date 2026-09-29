import { IsArray, IsString } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class CompareArticlesDto {
  @ApiProperty({ example: ['900001', '900002', '900003'], minItems: 2, maxItems: 10 })
  @IsArray()
  @IsString({ each: true })
  codes!: string[];
}
