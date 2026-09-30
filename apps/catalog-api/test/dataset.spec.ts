import 'dotenv/config';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

describe('deterministic V1 seed', () => {
  const read = (name: string): Buffer => readFileSync(resolve('data/seed', name));
  const articles = JSON.parse(read('articles.v1.json').toString()) as Array<
    Record<string, Record<string, unknown>>
  >;
  const sheets = JSON.parse(read('technical-sheets.v1.json').toString()) as Array<{
    articulo_codigo: string;
  }>;
  const users = JSON.parse(read('demo-users.v1.json').toString()) as Array<{ id: string }>;

  it('contains the exact article range and active distribution', () => {
    const codes = articles.map((item) => item.identificacion.codigo);
    expect(articles).toHaveLength(50);
    expect(new Set(codes).size).toBe(50);
    expect(codes).toEqual(Array.from({ length: 50 }, (_, index) => String(900001 + index)));
    expect(articles.filter((item) => item.identificacion.activo).length).toBe(42);
    expect(articles.filter((item) => !item.identificacion.activo).length).toBe(8);
    expect(Object.values(articles[0]).flatMap((group) => Object.keys(group))).toHaveLength(90);
  });

  it('contains one valid metadata-only sheet per article and both users', () => {
    expect(sheets).toHaveLength(50);
    expect(sheets.map((sheet) => sheet.articulo_codigo)).toEqual(
      articles.map((item) => item.identificacion.codigo),
    );
    expect(users.map((user) => user.id)).toEqual(['demo-user-01', 'demo-user-02']);
    expect(Object.keys(JSON.parse(read('technical-sheets.v1.json').toString())[0])).toEqual([
      'ficha_id',
      'articulo_codigo',
      'titulo',
      'version',
      'idioma',
      'estado',
      'created_at',
      'updated_at',
      'source_note',
    ]);
  });

  it.each([
    ['articles.v1.json', 'ad38929319a6b40d40aece1079712a26999a0f335558f1fbf28ed5bd4d1ac934'],
    [
      'technical-sheets.v1.json',
      '1d5f91ea8b728abaf99373ddcb6fd726aa83aa5b8a828942487909c08606a1c2',
    ],
    ['demo-users.v1.json', '509c0b08539b087809746b08c18c6876625f3e5626c392e0d9fa6615d3f68265'],
  ])('keeps the explicit SHA-256 for %s', (name, expected) => {
    expect(createHash('sha256').update(read(name)).digest('hex')).toBe(expected);
  });
});
