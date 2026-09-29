import { Controller, Get, Param } from '@nestjs/common';
import { ApiOperation, ApiTags } from '@nestjs/swagger';
import { TechnicalSheetsService } from './technical-sheets.service';

@ApiTags('technical-sheets')
@Controller()
export class TechnicalSheetsController {
  constructor(private readonly sheets: TechnicalSheetsService) {}
  @Get('technical-sheets/:fichaId')
  @ApiOperation({ summary: 'Obtiene metadatos de una ficha ficticia' })
  byId(@Param('fichaId') id: string): Promise<object> {
    return this.sheets.byId(id);
  }
  @Get('articles/:codigo/technical-sheet')
  @ApiOperation({ summary: 'Obtiene la ficha asociada al artículo' })
  byArticle(@Param('codigo') code: string): Promise<object> {
    return this.sheets.byArticle(code);
  }
}
