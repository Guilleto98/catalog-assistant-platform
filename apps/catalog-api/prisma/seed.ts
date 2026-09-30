import 'dotenv/config';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { PrismaClient, type Prisma } from '@prisma/client';

interface SeedArticle {
  identificacion: Record<string, unknown>;
  producto_destino: Record<string, unknown>;
  codigos_asociaciones: Record<string, unknown>;
  envase_pesaje: Record<string, unknown>;
  etiquetado: Record<string, unknown>;
  fechas_operacion: Record<string, unknown>;
  comercial_operativo: Record<string, unknown>;
  calidad_seguridad: Record<string, unknown>;
  metadata: Record<string, unknown>;
}
interface SeedSheet {
  ficha_id: string;
  articulo_codigo: string;
  titulo: string;
  version: string;
  idioma: string;
  estado: string;
  created_at: string;
  updated_at: string;
  source_note: string;
}
interface SeedUser {
  id: string;
  display_name: string;
}

const prisma = new PrismaClient();
async function json<T>(name: string): Promise<T> {
  return JSON.parse(await readFile(resolve('data/seed', name), 'utf8')) as T;
}

async function main(): Promise<void> {
  const [articles, sheets, users] = await Promise.all([
    json<SeedArticle[]>('articles.v1.json'),
    json<SeedSheet[]>('technical-sheets.v1.json'),
    json<SeedUser[]>('demo-users.v1.json'),
  ]);
  await prisma.savedFilter.deleteMany();
  await prisma.technicalSheet.deleteMany();
  await prisma.article.deleteMany();
  await prisma.demoUser.deleteMany();
  for (const article of articles) {
    const id = article.identificacion;
    const product = article.producto_destino;
    await prisma.article.create({
      data: {
        codigo: String(id.codigo),
        activo: Boolean(id.activo),
        corte: String(product.corte),
        mercado: String(product.mercado),
        paisDestino: String(product.pais_destino),
        temperatura: String(product.temperatura),
        vidaUtilDias: Number(product.vida_util),
        nombreBusqueda: String(id.nombre).toLowerCase(),
        identificacion: article.identificacion as Prisma.InputJsonValue,
        productoDestino: article.producto_destino as Prisma.InputJsonValue,
        codigosAsociaciones: article.codigos_asociaciones as Prisma.InputJsonValue,
        envasePesaje: article.envase_pesaje as Prisma.InputJsonValue,
        etiquetado: article.etiquetado as Prisma.InputJsonValue,
        fechasOperacion: article.fechas_operacion as Prisma.InputJsonValue,
        comercialOperativo: article.comercial_operativo as Prisma.InputJsonValue,
        calidadSeguridad: article.calidad_seguridad as Prisma.InputJsonValue,
        metadata: article.metadata as Prisma.InputJsonValue,
      },
    });
  }
  for (const sheet of sheets)
    await prisma.technicalSheet.create({
      data: {
        fichaId: sheet.ficha_id,
        articuloCodigo: sheet.articulo_codigo,
        titulo: sheet.titulo,
        version: sheet.version,
        idioma: sheet.idioma,
        estado: sheet.estado,
        createdAt: new Date(sheet.created_at),
        updatedAt: new Date(sheet.updated_at),
        sourceNote: sheet.source_note,
      },
    });
  for (const user of users)
    await prisma.demoUser.create({ data: { id: user.id, displayName: user.display_name } });
  console.log(
    `Seeded ${articles.length} articles, ${sheets.length} sheets and ${users.length} users.`,
  );
}
void main()
  .catch((error: unknown) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => prisma.$disconnect());
