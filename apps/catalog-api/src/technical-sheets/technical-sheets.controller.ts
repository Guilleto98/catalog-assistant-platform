import { Controller, Get, Param } from '@nestjs/common';
import { ApiOkResponse, ApiOperation, ApiTags } from '@nestjs/swagger';
import { TechnicalSheetsService } from './technical-sheets.service';
import type { TechnicalSheetResponse } from '../common/types/api-responses';
import { TechnicalSheetResponseDto } from '../common/dto/api-responses.dto';

@ApiTags('technical-sheets')
@Controller()
export class TechnicalSheetsController {
  constructor(private readonly sheets: TechnicalSheetsService) {}
  @Get('technical-sheets/:fichaId')
  @ApiOperation({ summary: 'Obtiene metadatos de una ficha ficticia' })
  @ApiOkResponse({ type: TechnicalSheetResponseDto })
  byId(@Param('fichaId') id: string): Promise<TechnicalSheetResponse> {
    return this.sheets.byId(id);
  }
  @Get('articles/:codigo/technical-sheet')
  @ApiOperation({ summary: 'Obtiene la ficha asociada al artículo' })
  @ApiOkResponse({ type: TechnicalSheetResponseDto })
  byArticle(@Param('codigo') code: string): Promise<TechnicalSheetResponse> {
    return this.sheets.byArticle(code);
  }
}
