-- CreateTable
CREATE TABLE "Article" (
    "codigo" TEXT NOT NULL PRIMARY KEY,
    "activo" BOOLEAN NOT NULL,
    "corte" TEXT NOT NULL,
    "mercado" TEXT NOT NULL,
    "paisDestino" TEXT NOT NULL,
    "temperatura" TEXT NOT NULL,
    "vidaUtilDias" INTEGER NOT NULL,
    "nombreBusqueda" TEXT NOT NULL,
    "identificacion" JSONB NOT NULL,
    "productoDestino" JSONB NOT NULL,
    "codigosAsociaciones" JSONB NOT NULL,
    "envasePesaje" JSONB NOT NULL,
    "etiquetado" JSONB NOT NULL,
    "fechasOperacion" JSONB NOT NULL,
    "comercialOperativo" JSONB NOT NULL,
    "calidadSeguridad" JSONB NOT NULL,
    "metadata" JSONB NOT NULL
);
CREATE TABLE "TechnicalSheet" (
    "fichaId" TEXT NOT NULL PRIMARY KEY,
    "articuloCodigo" TEXT NOT NULL,
    "titulo" TEXT NOT NULL,
    "version" TEXT NOT NULL,
    "idioma" TEXT NOT NULL,
    "estado" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL,
    "updatedAt" DATETIME NOT NULL,
    "sourceNote" TEXT NOT NULL,
    CONSTRAINT "TechnicalSheet_articuloCodigo_fkey" FOREIGN KEY ("articuloCodigo") REFERENCES "Article" ("codigo") ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE UNIQUE INDEX "TechnicalSheet_articuloCodigo_key" ON "TechnicalSheet"("articuloCodigo");
CREATE TABLE "DemoUser" ("id" TEXT NOT NULL PRIMARY KEY, "displayName" TEXT NOT NULL);
CREATE TABLE "SavedFilter" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "ownerUserId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "search" JSONB NOT NULL,
    "createdAt" DATETIME NOT NULL,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "SavedFilter_ownerUserId_fkey" FOREIGN KEY ("ownerUserId") REFERENCES "DemoUser" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE INDEX "Article_corte_mercado_temperatura_idx" ON "Article"("corte", "mercado", "temperatura");
CREATE INDEX "SavedFilter_ownerUserId_idx" ON "SavedFilter"("ownerUserId");
