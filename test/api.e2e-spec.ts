import 'dotenv/config';
import { ValidationPipe } from '@nestjs/common';
import type { INestApplication } from '@nestjs/common';
import { Test } from '@nestjs/testing';
import request from 'supertest';
import { AppModule } from '../src/app.module';
import { ApiExceptionFilter } from '../src/common/errors/api-exception.filter';

describe('Uruguay Meat Catalog API (e2e)', () => {
  let app: INestApplication;
  const api = (): ReturnType<typeof request> => request(app.getHttpServer());
  const codes = (response: { body: { items: Array<{ codigo: string }> } }): string[] =>
    response.body.items.map((item) => item.codigo);

  beforeAll(async () => {
    const module = await Test.createTestingModule({ imports: [AppModule] }).compile();
    app = module.createNestApplication();
    app.setGlobalPrefix('api/v1');
    app.useGlobalPipes(
      new ValidationPipe({ transform: true, whitelist: true, forbidNonWhitelisted: true }),
    );
    app.useGlobalFilters(new ApiExceptionFilter());
    await app.init();
    await app.listen(0, '127.0.0.1');
  });
  afterAll(async () => app.close());

  it('reports health and filter metadata consistent with the whitelist', async () => {
    await api()
      .get('/api/v1/health')
      .expect(200, { status: 'ok', dataset_version: 'v1', articles: 50 });
    const metadata = await api().get('/api/v1/metadata/filterable-fields').expect(200);
    const temp = metadata.body.fields.find(
      (field: { path: string }) => field.path === 'producto_destino.temperatura',
    );
    expect(temp).toMatchObject({
      type: 'string',
      nullable: false,
      unit: null,
      operators: ['eq', 'neq', 'in'],
      allowed_values: ['REFRIGERADO', 'CONGELADO'],
    });
    await api()
      .post('/api/v1/articles/search')
      .send({ filters: [{ field: 'metadata.origen_dato', operator: 'eq', value: 'x' }] })
      .expect(400)
      .expect(({ body }) => expect(body.error.code).toBe('INVALID_FILTER_FIELD'));
  });

  it.each([
    ['eq', { field: 'producto_destino.corte', operator: 'eq', value: 'BIFE_ANCHO' }, 5],
    ['neq', { field: 'producto_destino.temperatura', operator: 'neq', value: 'CONGELADO' }, 20],
    ['in', { field: 'producto_destino.mercado', operator: 'in', value: ['CHINA', 'BRASIL'] }, 20],
    ['contains', { field: 'identificacion.nombre', operator: 'contains', value: 'bife ancho' }, 5],
    ['gte', { field: 'producto_destino.vida_util', operator: 'gte', value: 395 }, 12],
    ['lte', { field: 'producto_destino.vida_util', operator: 'lte', value: 93 }, 4],
    [
      'between',
      { field: 'envase_pesaje.peso_promedio_kg', operator: 'between', value: [15, 16] },
      5,
    ],
    ['is_null', { field: 'codigos_asociaciones.codigo_inac', operator: 'is_null' }, 7],
  ])('supports %s', async (_name, filter, total) => {
    const response = await api()
      .post('/api/v1/articles/search')
      .send({ filters: [filter], page_size: 50 })
      .expect(201);
    expect(response.body.pagination.total_items).toBe(total);
  });

  it('combines filters, sorts, paginates and returns exact totals', async () => {
    const response = await api()
      .post('/api/v1/articles/search')
      .send({
        filters: [{ field: 'producto_destino.temperatura', operator: 'eq', value: 'CONGELADO' }],
        sort: [{ field: 'identificacion.codigo', direction: 'desc' }],
        page: 2,
        page_size: 3,
      })
      .expect(201);
    expect(response.body.pagination).toEqual({
      page: 2,
      page_size: 3,
      total_items: 30,
      total_pages: 10,
    });
    expect(codes(response)).toEqual(['900045', '900044', '900041']);
  });

  it('rejects invalid operators, types, enums and pagination', async () => {
    const cases = [
      [
        { filters: [{ field: 'producto_destino.vida_util', operator: 'contains', value: 3 }] },
        'INVALID_FILTER_OPERATOR',
      ],
      [
        { filters: [{ field: 'producto_destino.vida_util', operator: 'gte', value: '365' }] },
        'INVALID_FILTER_VALUE',
      ],
      [
        { filters: [{ field: 'producto_destino.mercado', operator: 'eq', value: 'MARTE' }] },
        'INVALID_FILTER_VALUE',
      ],
      [{ page_size: 51 }, 'INVALID_PAGINATION'],
    ];
    for (const [body, code] of cases)
      await api()
        .post('/api/v1/articles/search')
        .send(body)
        .expect(400)
        .expect(({ body: result }) => expect(result.error.code).toBe(code));
  });

  it('returns exact reference searches A, B and C', async () => {
    const a = await api()
      .post('/api/v1/articles/search')
      .send({
        filters: [
          { field: 'producto_destino.corte', operator: 'eq', value: 'BIFE_ANCHO' },
          { field: 'producto_destino.mercado', operator: 'eq', value: 'CHINA' },
        ],
        page_size: 50,
      });
    expect(codes(a)).toEqual(['900001']);
    const b = await api()
      .post('/api/v1/articles/search')
      .send({
        filters: [{ field: 'producto_destino.vida_util', operator: 'gte', value: 395 }],
        page_size: 50,
      });
    expect(codes(b)).toEqual([
      '900031',
      '900034',
      '900035',
      '900036',
      '900039',
      '900040',
      '900041',
      '900044',
      '900045',
      '900046',
      '900049',
      '900050',
    ]);
    const c = await api()
      .post('/api/v1/articles/search')
      .send({
        filters: [{ field: 'codigos_asociaciones.codigo_inac', operator: 'is_null' }],
        page_size: 50,
      });
    expect(codes(c)).toEqual([
      '900007',
      '900014',
      '900021',
      '900028',
      '900035',
      '900042',
      '900049',
    ]);
  });

  it('gets details and consistent metadata-only technical sheets', async () => {
    const article = await api().get('/api/v1/articles/900014').expect(200);
    expect(article.body.ficha_id).toBe('FT-DEMO-900014');
    const byArticle = await api().get('/api/v1/articles/900014/technical-sheet').expect(200);
    const byId = await api().get('/api/v1/technical-sheets/FT-DEMO-900014').expect(200);
    expect(byArticle.body).toEqual(byId.body);
    expect(byId.body).not.toHaveProperty('sections');
    await api()
      .get('/api/v1/articles/900999')
      .expect(404)
      .expect(({ body }) => expect(body.error.code).toBe('ARTICLE_NOT_FOUND'));
  });

  it('compares two and three articles, including null as a value', async () => {
    await api()
      .post('/api/v1/articles/compare')
      .send({ codes: ['900001'] })
      .expect(400)
      .expect(({ body }) => expect(body.error.code).toBe('INVALID_COMPARISON'));
    const two = await api()
      .post('/api/v1/articles/compare')
      .send({ codes: ['900007', '900008'] })
      .expect(201);
    const inac = two.body.fields.find(
      (field: { field: string }) => field.field === 'codigos_asociaciones.codigo_inac',
    );
    expect(inac).toMatchObject({
      values: { '900007': null, '900008': 'INAC-DEMO-008' },
      different: true,
    });
    const three = await api()
      .post('/api/v1/articles/compare')
      .send({ codes: ['900001', '900002', '900003'] })
      .expect(201);
    expect(three.body.different_fields_count + three.body.equal_fields_count).toBe(21);
    expect(
      three.body.fields.find((field: { field: string }) => field.field === 'identificacion.especie')
        .different,
    ).toBe(false);
    await api()
      .post('/api/v1/articles/compare')
      .send({ codes: ['900001', '900999'] })
      .expect(404);
  });

  it('separates high-score ineligible candidates from eligible candidates', async () => {
    const response = await api()
      .post('/api/v1/articles/similar')
      .send({
        reference_code: '900001',
        required: {
          'producto_destino.mercado': 'CHINA',
          'producto_destino.temperatura': 'CONGELADO',
        },
        limit: 10,
      })
      .expect(201);
    expect(response.body.eligible_candidates[0]).toMatchObject({
      codigo: '900006',
      similarity_score: 70,
      eligibility: 'ELIGIBLE',
    });
    const rejected = response.body.ineligible_candidates.find(
      (item: { codigo: string }) => item.codigo === '900004',
    );
    expect(rejected).toMatchObject({ similarity_score: 90, eligibility: 'INELIGIBLE' });
    expect(
      response.body.eligible_candidates.some(
        (item: { codigo: string }) => item.codigo === '900001',
      ),
    ).toBe(false);
  });

  it('supports feature normalization, ties, NOT_AVAILABLE and no eligible candidates', async () => {
    await api()
      .post('/api/v1/articles/similar')
      .send({ reference_code: '900001', features: { 'identificacion.especie': 'BOVINO' } })
      .expect(400)
      .expect(({ body }) => expect(body.error.code).toBe('INVALID_SIMILARITY_REQUEST'));
    const tie = await api()
      .post('/api/v1/articles/similar')
      .send({ features: { 'identificacion.especie': 'BOVINO' }, limit: 3 })
      .expect(201);
    expect(tie.body.eligible_candidates.map((item: { codigo: string }) => item.codigo)).toEqual([
      '900001',
      '900002',
      '900003',
    ]);
    const missing = await api()
      .post('/api/v1/articles/similar')
      .send({
        reference_code: '900001',
        required: { 'envase_pesaje.envase_exterior': 'CAJA_CARTON' },
      })
      .expect(201);
    expect(
      missing.body.ineligible_candidates.find(
        (item: { codigo: string }) => item.codigo === '900011',
      ).required_evaluation[0].status,
    ).toBe('NOT_AVAILABLE');
    const none = await api()
      .post('/api/v1/articles/similar')
      .send({
        reference_code: '900001',
        required: {
          'producto_destino.mercado': 'CHINA',
          'producto_destino.presentacion': 'CON_HUESO',
        },
      })
      .expect(201);
    expect(none.body.eligible_candidates).toEqual([]);
  });

  it('enforces saved-filter ownership through create, list, get, execute and delete', async () => {
    await api()
      .get('/api/v1/saved-filters')
      .expect(400)
      .expect(({ body }) => expect(body.error.code).toBe('DEMO_USER_REQUIRED'));
    await api()
      .get('/api/v1/saved-filters')
      .set('X-Demo-User-Id', 'unknown')
      .expect(404)
      .expect(({ body }) => expect(body.error.code).toBe('DEMO_USER_NOT_FOUND'));
    const created = await api()
      .post('/api/v1/saved-filters')
      .set('X-Demo-User-Id', 'demo-user-01')
      .send({
        name: 'China congelados',
        description: 'Productos congelados destinados a China',
        search: {
          filters: [
            { field: 'producto_destino.mercado', operator: 'eq', value: 'CHINA' },
            { field: 'producto_destino.temperatura', operator: 'eq', value: 'CONGELADO' },
          ],
          sort: [],
        },
      })
      .expect(201);
    const id = created.body.id;
    expect(
      (await api().get('/api/v1/saved-filters').set('X-Demo-User-Id', 'demo-user-01')).body,
    ).toHaveLength(1);
    expect(
      (await api().get('/api/v1/saved-filters').set('X-Demo-User-Id', 'demo-user-02')).body,
    ).toHaveLength(0);
    for (const method of ['get', 'post', 'delete'] as const) {
      const path =
        method === 'post' ? `/api/v1/saved-filters/${id}/execute` : `/api/v1/saved-filters/${id}`;
      await api()
        [method](path)
        .set('X-Demo-User-Id', 'demo-user-02')
        .expect(404)
        .expect(({ body }) => expect(body.error.code).toBe('SAVED_FILTER_NOT_FOUND'));
    }
    const execution = await api()
      .post(`/api/v1/saved-filters/${id}/execute`)
      .set('X-Demo-User-Id', 'demo-user-01')
      .expect(200);
    expect(execution.body.pagination.total_items).toBe(10);
    await api()
      .delete(`/api/v1/saved-filters/${id}`)
      .set('X-Demo-User-Id', 'demo-user-01')
      .expect(204);
  });
});
