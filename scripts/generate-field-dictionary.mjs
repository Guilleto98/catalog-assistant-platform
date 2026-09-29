import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { FIELD_METADATA } = require('../dist/common/metadata/field-metadata.js');
const articles = JSON.parse(readFileSync(new URL('../data/seed/articles.v1.json', import.meta.url)));
const central = new Map(FIELD_METADATA.map((field) => [field.path, field]));
const units = { vida_util: 'dias', peso_envase_primario_kg: 'kg', peso_envase_exterior_kg: 'kg', tara_total_kg: 'kg', peso_promedio_kg: 'kg', peso_minimo_kg: 'kg', peso_maximo_kg: 'kg', largo_cm: 'cm', ancho_cm: 'cm', alto_cm: 'cm', fecha_creacion: 'ISO-8601', fecha_actualizacion: 'ISO-8601' };
const rows = [];
for (const [group, values] of Object.entries(articles[0])) {
  for (const key of Object.keys(values)) {
    const path = `${group}.${key}`; const meta = central.get(path); const all = articles.map((a) => a[group][key]); const example = all.find((v) => v !== null) ?? null;
    const type = meta?.type ?? (typeof example === 'number' ? 'number' : typeof example === 'boolean' ? 'boolean' : 'string');
    const nullable = all.some((value) => value === null);
    const allowed = meta?.allowed_values ? meta.allowed_values.join(', ') : '—';
    rows.push(`| \`${path}\` | ${key.replaceAll('_',' ')} | ${type} | ${nullable ? 'sí' : 'no'} | ${meta?.unit ?? units[key] ?? '—'} | ${meta?.description ?? `Dato sintético de ${key.replaceAll('_',' ')}`} | \`${String(example)}\` | ${meta?.filterable ? 'sí' : 'no'} | ${meta?.operators?.join(', ') ?? '—'} | ${allowed} | ${meta?.comparable ? 'sí' : 'no'} | ${meta?.used_for_similarity ? 'sí' : 'no'} | ${meta?.can_be_required ? 'sí' : 'no'} |`);
  }
}
const header = `# Diccionario de campos\n\nEste diccionario se genera desde el seed V1 y la definición central \`FIELD_METADATA\`. “Nullable” refleja los 50 registros. Solo los paths con **filtrable = sí** son aceptados por search. Todos los valores son sintéticos; ninguna marca, rito o referencia implica certificación real.\n\n| path | nombre | tipo | nullable | unidad | descripción | ejemplo | filtrable | operadores permitidos | valores permitidos | comparable | utilizado para similitud | puede ser obligatorio |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|\n`;
writeFileSync(new URL('../docs/field_dictionary.md', import.meta.url), header + rows.join('\n') + '\n');
console.log(`Documented ${rows.length} fields.`);
