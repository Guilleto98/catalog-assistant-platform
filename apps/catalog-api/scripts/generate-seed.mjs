import { mkdirSync, writeFileSync } from 'node:fs';

const families = [
  ['BIFE_ANCHO', 'Bife ancho', 'DORSAL'], ['BIFE_ANGOSTO', 'Bife angosto', 'DORSAL'],
  ['LOMO', 'Lomo', 'LOMO'], ['CUADRIL', 'Cuadril', 'TRASERO'],
  ['COLITA_DE_CUADRIL', 'Colita de cuadril', 'TRASERO'], ['NALGA', 'Nalga', 'TRASERO'],
  ['PECETO', 'Peceto', 'TRASERO'], ['VACIO', 'Vacío', 'ABDOMINAL'],
  ['ASADO_DE_TIRA', 'Asado de tira', 'COSTILLAR'], ['PALETA', 'Paleta', 'DELANTERO'],
];
const variants = [
  ['CHINA','CHINA','CONGELADO','SIN_HUESO','zh','VACIO','CAJA_CARTON'],
  ['BRASIL','BRASIL','REFRIGERADO','SIN_HUESO','pt','VACIO','CAJA_CARTON'],
  ['URUGUAY','URUGUAY','REFRIGERADO','PORCIONADO','es','FLOWPACK','CAJON_PLASTICO'],
  ['UE','ESPANA','CONGELADO','SIN_HUESO','es','VACIO','CAJA_CARTON'],
  ['EEUU','ESTADOS_UNIDOS','CONGELADO','CON_HUESO','en','VACIO','CAJA_CARTON'],
];
const created = '2026-01-01T00:00:00.000Z';
const updated = '2026-06-01T00:00:00.000Z';
const articles = [];
for (let familyIndex = 0; familyIndex < families.length; familyIndex++) {
  const [cut, label, anatomical] = families[familyIndex];
  for (let variantIndex = 0; variantIndex < variants.length; variantIndex++) {
    const index = familyIndex * 5 + variantIndex + 1;
    const code = String(900000 + index);
    const [market,country,temp,presentation,language,primary,outer] = variants[variantIndex];
    const active = index <= 42;
    const shelfLife = temp === 'CONGELADO' ? 365 + familyIndex * 5 : 90 + familyIndex * 3;
    const avg = index % 11 === 0 ? null : Number((12 + familyIndex * 1.2 + variantIndex * 0.8).toFixed(2));
    const inac = index % 7 === 0 ? null : `INAC-DEMO-${String(index).padStart(3,'0')}`;
    const effectiveOuter = index === 11 ? null : outer;
    const bone = presentation === 'CON_HUESO';
    articles.push({
      identificacion: { codigo: code, codigo_alternativo: `ALT-${code}`, nombre: `${label} ${temp.toLowerCase()} ${market}`, nombre_corto: label, tipo: 'CARNE_BOVINA', subtipo: bone ? 'CORTE_CON_HUESO' : 'CORTE_SIN_HUESO', especie: 'BOVINO', familia: cut, grupo: 'CORTES_BOVINOS', subgrupo: anatomical, grupo_anatomico: anatomical, grupo_madre: 'CARNE', nivel: 3, activo: active, descripcion_etiqueta: `${label.toUpperCase()} - DEMO` },
      producto_destino: { corte: cut, presentacion: presentation, mercado: market, pais_destino: country, region_destino: market === 'UE' ? 'EUROPA' : market === 'CHINA' ? 'ASIA' : 'AMERICA', temperatura: temp, condicion_almacenamiento: `${temp}_DEMO`, vida_util: shelfLife, vida_util_unidad: 'DIAS', uso_previsto: 'CONSUMO_HUMANO_DEMO', categoria: 'CORTE_PRIMARIO', con_hueso: bone, marmoleo: familyIndex % 3 === 0 ? 'MEDIO_DEMO' : 'BAJO_DEMO', clasificacion: `CLASE_DEMO_${(familyIndex % 3) + 1}`, estado_producto: 'CRUDO', pais_origen_demo: 'URUGUAY', observacion_destino: variantIndex === 4 ? 'Destino educativo EEUU' : null },
      codigos_asociaciones: { codigo_inac: inac, asociacion_inac: inac ? `ASOC-${inac}` : null, codigo_internacional: `INT-DEMO-${code}`, codigo_cliente: index % 9 === 0 ? null : `CLI-${market}-${code}`, codigo_gs1: `GS1-DEMO-${code}`, indicador_angus: familyIndex % 4 === 0, sku_interno: `SKU-${code}`, codigo_exportacion: `EXP-DEMO-${market}-${code}` },
      envase_pesaje: { envase_primario: primary, envase_exterior: effectiveOuter, material_envase_primario: primary === 'FLOWPACK' ? 'FILM_DEMO' : 'BOLSA_MULTICAPA_DEMO', material_envase_exterior: effectiveOuter === null ? null : outer === 'CAJA_CARTON' ? 'CARTON_DEMO' : 'PLASTICO_DEMO', codigo_envase_primario: `EP-${variantIndex + 1}`, codigo_envase_exterior: effectiveOuter === null ? null : `EE-${variantIndex + 1}`, peso_envase_primario_kg: 0.08, peso_envase_exterior_kg: effectiveOuter === null ? null : 0.65, tara_total_kg: effectiveOuter === null ? 0.08 : 0.73, unidad_stock: 'CAJA', piezas_por_caja: 4 + variantIndex, tipo_peso: variantIndex % 2 === 0 ? 'VARIABLE' : 'FIJO', peso_promedio_kg: avg, peso_minimo_kg: avg === null ? null : Number((avg - 2).toFixed(2)), peso_maximo_kg: avg === null ? null : Number((avg + 2).toFixed(2)), calibre_minimo: familyIndex + 1, calibre_maximo: familyIndex + 3, largo_cm: 60 + familyIndex, ancho_cm: 40 + variantIndex, alto_cm: 20 + variantIndex },
      etiquetado: { etiqueta_interna: `ETI-INT-${code}`, etiqueta_externa: `ETI-EXT-${code}`, descripcion_alternativa: `${label} demo alternativa`, descripcion_reportes: `${label} / ${market}`, descripcion_cliente: `${label} para ${market}`, descripcion_proforma: `${label} ${presentation}`, idioma_etiqueta: language, idioma_cliente: language, rito: market === 'CHINA' && familyIndex % 2 === 0 ? 'HALAL_DEMO_NO_CERTIFICADO' : null, marca: 'MARCA_DEMO_NO_REAL', leyenda_comercial: 'PRODUCTO SINTETICO EDUCATIVO' },
      fechas_operacion: { corrimiento_faena: 0, corrimiento_produccion: 1, corrimiento_congelacion: temp === 'CONGELADO' ? 1 : null, corrimiento_vencimiento: shelfLife, unidad_corrimiento: 'DIAS', fecha_creacion: created, fecha_actualizacion: updated, turno_preferente: variantIndex % 2 ? 'TARDE' : 'MANANA', planta_demo: `PLANTA_DEMO_${(familyIndex % 2) + 1}`, linea_produccion_demo: `LINEA_DEMO_${(variantIndex % 3) + 1}` },
      comercial_operativo: { canal_venta_demo: market === 'URUGUAY' ? 'LOCAL_DEMO' : 'EXPORTACION_DEMO', pedido_minimo_cajas_demo: 10 + variantIndex },
      calidad_seguridad: { estado_validacion: 'NO_VALIDADO_DEMO', referencia_calidad: 'DATO_SINTETICO_NO_VALIDADO' },
      metadata: { version_dataset: 'v1', origen_dato: 'GENERADOR_DETERMINISTICO_EDUCATIVO', dato_sintetico: true, tiene_datos_incompletos: inac === null || avg === null || effectiveOuter === null, observaciones_demo: 'No representa datos, certificaciones ni recomendaciones oficiales' }
    });
  }
}
const sheets = articles.map((article) => ({ ficha_id: `FT-DEMO-${article.identificacion.codigo}`, articulo_codigo: article.identificacion.codigo, titulo: `Ficha técnica demo - ${article.identificacion.codigo}`, version: '1.0-demo', idioma: 'es', estado: 'SINTETICA_NO_OFICIAL', created_at: created, updated_at: updated, source_note: 'Ficha ficticia para demostración. No existe PDF oficial asociado.' }));
const users = [{ id: 'demo-user-01', display_name: 'Usuario Demo 1' }, { id: 'demo-user-02', display_name: 'Usuario Demo 2' }];
mkdirSync(new URL('../data/seed/', import.meta.url), { recursive: true });
writeFileSync(new URL('../data/seed/articles.v1.json', import.meta.url), JSON.stringify(articles, null, 2) + '\n');
writeFileSync(new URL('../data/seed/technical-sheets.v1.json', import.meta.url), JSON.stringify(sheets, null, 2) + '\n');
writeFileSync(new URL('../data/seed/demo-users.v1.json', import.meta.url), JSON.stringify(users, null, 2) + '\n');
console.log(`Generated ${articles.length} articles, ${sheets.length} sheets, ${users.length} users.`);
