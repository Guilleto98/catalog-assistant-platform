import { Body, Controller, Delete, Get, Headers, HttpCode, Param, Post } from '@nestjs/common';
import { ApiHeader, ApiOperation, ApiTags } from '@nestjs/swagger';
import { CreateSavedFilterDto } from './dto/create-saved-filter.dto';
import { SavedFiltersService } from './saved-filters.service';

@ApiTags('saved-filters')
@ApiHeader({
  name: 'X-Demo-User-Id',
  required: true,
  example: 'demo-user-01',
  description: 'Simula usuario; no es autenticación',
})
@Controller('saved-filters')
export class SavedFiltersController {
  constructor(private readonly filters: SavedFiltersService) {}
  @Post()
  @ApiOperation({ summary: 'Guarda criterios, no resultados' })
  create(
    @Headers('x-demo-user-id') user: string | undefined,
    @Body() dto: CreateSavedFilterDto,
  ): Promise<object> {
    return this.filters.create(user, dto);
  }
  @Get() list(@Headers('x-demo-user-id') user?: string): Promise<object[]> {
    return this.filters.list(user);
  }
  @Get(':id') get(
    @Headers('x-demo-user-id') user: string | undefined,
    @Param('id') id: string,
  ): Promise<object> {
    return this.filters.getSerialized(user, id);
  }
  @Post(':id/execute') @HttpCode(200) execute(
    @Headers('x-demo-user-id') user: string | undefined,
    @Param('id') id: string,
  ): Promise<object> {
    return this.filters.execute(user, id);
  }
  @Delete(':id') @HttpCode(204) async remove(
    @Headers('x-demo-user-id') user: string | undefined,
    @Param('id') id: string,
  ): Promise<void> {
    await this.filters.remove(user, id);
  }
}
