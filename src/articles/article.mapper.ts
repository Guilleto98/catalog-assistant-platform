import type { Article } from '@prisma/client';
import type { ArticleDocument, ArticleGroup } from '../common/types/article.types';

export function toDocument(article: Article, fichaId?: string): ArticleDocument {
  return {
    identificacion: article.identificacion as ArticleGroup,
    producto_destino: article.productoDestino as ArticleGroup,
    codigos_asociaciones: article.codigosAsociaciones as ArticleGroup,
    envase_pesaje: article.envasePesaje as ArticleGroup,
    etiquetado: article.etiquetado as ArticleGroup,
    fechas_operacion: article.fechasOperacion as ArticleGroup,
    comercial_operativo: article.comercialOperativo as ArticleGroup,
    calidad_seguridad: article.calidadSeguridad as ArticleGroup,
    metadata: article.metadata as ArticleGroup,
    ...(fichaId ? { ficha_id: fichaId } : {}),
  };
}

export function getPath(document: ArticleDocument, path: string): unknown {
  const [group, property] = path.split('.');
  if (!group || !property) return undefined;
  const value = document[group as keyof ArticleDocument];
  return typeof value === 'object' && value !== null ? value[property] : undefined;
}
