import { ArrayMaxSize, ArrayMinSize, IsArray, IsString } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';
import { COMPARISON_POLICY } from '../../common/constants/api.constants';

export class CompareArticlesDto {
  @ApiProperty({
    example: ['900001', '900002', '900003'],
    minItems: COMPARISON_POLICY.MIN_ARTICLES,
    maxItems: COMPARISON_POLICY.MAX_ARTICLES,
  })
  @IsArray()
  @ArrayMinSize(COMPARISON_POLICY.MIN_ARTICLES)
  @ArrayMaxSize(COMPARISON_POLICY.MAX_ARTICLES)
  @IsString({ each: true })
  codes!: string[];
}
