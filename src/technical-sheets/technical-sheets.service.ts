import { HttpStatus, Injectable } from '@nestjs/common';
import { ApiError } from '../common/errors/api-error';
import { PrismaService } from '../database/prisma.service';

@Injectable()
export class TechnicalSheetsService {
  constructor(private readonly prisma: PrismaService) {}
  async byId(fichaId: string): Promise<object> {
    const sheet = await this.prisma.technicalSheet.findUnique({ where: { fichaId } });
    if (!sheet)
      throw new ApiError(
        'TECHNICAL_SHEET_NOT_FOUND',
        `Technical sheet ${fichaId} was not found`,
        HttpStatus.NOT_FOUND,
      );
    return this.serialize(sheet);
  }
  async byArticle(codigo: string): Promise<object> {
    const sheet = await this.prisma.technicalSheet.findUnique({
      where: { articuloCodigo: codigo },
    });
    if (!sheet)
      throw new ApiError(
        'ARTICLE_NOT_FOUND',
        `Article ${codigo} was not found`,
        HttpStatus.NOT_FOUND,
      );
    return this.serialize(sheet);
  }
  private serialize(sheet: {
    fichaId: string;
    articuloCodigo: string;
    titulo: string;
    version: string;
    idioma: string;
    estado: string;
    createdAt: Date;
    updatedAt: Date;
    sourceNote: string;
  }): object {
    return {
      ficha_id: sheet.fichaId,
      articulo_codigo: sheet.articuloCodigo,
      titulo: sheet.titulo,
      version: sheet.version,
      idioma: sheet.idioma,
      estado: sheet.estado,
      created_at: sheet.createdAt.toISOString(),
      updated_at: sheet.updatedAt.toISOString(),
      source_note: sheet.sourceNote,
    };
  }
}
