# Postman

## Importar y probar

1. Iniciar la API con `npm run start:dev` o `docker compose up --build`.
2. En Postman seleccionar **Import**.
3. Importar `Uruguay-Meat-Catalog-API.postman_collection.json`.
4. Abrir la colección y confirmar que `base_url` sea `http://localhost:3000/api/v1`.
5. Ejecutar requests individuales o usar **Run collection**.

La carpeta **05 - Filtros guardados** debe ejecutarse en orden: la primera request crea el filtro y guarda automáticamente su ID en `saved_filter_id`; la última lo elimina.

Los usuarios configurados son `demo-user-01` y `demo-user-02`. El header solo simula ownership y no es autenticación real.
