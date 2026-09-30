import {
  Body,
  Controller,
  Delete,
  Get,
  Headers,
  HttpCode,
  HttpStatus,
  Param,
  Post,
} from '@nestjs/common';
import {
  ApiCreatedResponse,
  ApiHeader,
  ApiNoContentResponse,
  ApiOkResponse,
  ApiOperation,
  ApiTags,
} from '@nestjs/swagger';
import { CreateSavedFilterDto } from './dto/create-saved-filter.dto';
import { SavedFiltersService } from './saved-filters.service';
import type { SavedFilterResponse, SearchArticlesResponse } from '../common/types/api-responses';
import { SavedFilterResponseDto, SearchArticlesResponseDto } from '../common/dto/api-responses.dto';

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
  @ApiCreatedResponse({ type: SavedFilterResponseDto })
  create(
    @Headers('x-demo-user-id') user: string | undefined,
    @Body() dto: CreateSavedFilterDto,
  ): Promise<SavedFilterResponse> {
    return this.filters.create(user, dto);
  }
  @Get()
  @ApiOkResponse({ type: [SavedFilterResponseDto] })
  list(@Headers('x-demo-user-id') user?: string): Promise<SavedFilterResponse[]> {
    return this.filters.list(user);
  }
  @Get(':id')
  @ApiOkResponse({ type: SavedFilterResponseDto })
  get(
    @Headers('x-demo-user-id') user: string | undefined,
    @Param('id') id: string,
  ): Promise<SavedFilterResponse> {
    return this.filters.getSerialized(user, id);
  }
  @Post(':id/execute')
  @HttpCode(HttpStatus.OK)
  @ApiOkResponse({ type: SearchArticlesResponseDto })
  execute(
    @Headers('x-demo-user-id') user: string | undefined,
    @Param('id') id: string,
  ): Promise<SearchArticlesResponse> {
    return this.filters.execute(user, id);
  }
  @Delete(':id')
  @HttpCode(HttpStatus.NO_CONTENT)
  @ApiNoContentResponse()
  async remove(
    @Headers('x-demo-user-id') user: string | undefined,
    @Param('id') id: string,
  ): Promise<void> {
    await this.filters.remove(user, id);
  }
}
