# Identidad y acceso — Etapa 6A

La Application API usa SQLite independiente del catálogo, SQLAlchemy 2.0 y
migraciones Alembic versionadas en `apps/agent/migrations`. El arranque aplica
`upgrade head`; no se regeneran tablas desde modelos. La base se crea con permiso
0600 y el directorio con 0700. Las foreign keys se habilitan en cada conexión.

`CLIENT_USER` opera sobre recursos propios dentro de su organización.
`INTERNAL_ADMIN` consulta usuarios, organizaciones, conversaciones y auditoría en
`/admin`. El acceso administrativo a conversaciones y ejecuciones genera su propio
evento. Los administradores no modifican conversaciones ajenas por la API normal.

Login: `POST /auth/login` con email y password. Se usa Argon2id, una cookie opaca
`solvo_session` y una sesión server-side que almacena únicamente SHA-256 del token
aleatorio. La cookie es HttpOnly, SameSite=Lax, Path=/ y Max-Age igual a
`AUTH_SESSION_TTL` (segundos, por defecto 28800). `AUTH_COOKIE_SECURE=true` debe
configurarse con HTTPS en producción. La expiración es absoluta: lastSeenAt no
extiende la sesión. `POST /auth/logout` revoca la sesión y borra la cookie.
`GET /auth/me` verifica también estado del usuario y organización en cada request.

Un email inexistente, una contraseña incorrecta y una identidad deshabilitada
devuelven el mismo error de login. Las razones se auditan internamente. No hay
registro público, OAuth, SSO, MFA ni recuperación de contraseña en esta etapa.

La CLI pide contraseñas sin mostrarlas ni incluirlas en argumentos:

```bash
npm run agent:bootstrap -- create-organization --name "Cliente A" --slug cliente-a
npm run agent:bootstrap -- create-user --email usuario@example.com --role CLIENT_USER --organization-id ID_ORGANIZACION --catalog-demo-user-id demo-user-01
npm run agent:bootstrap -- create-user --email interno@example.com --role INTERNAL_ADMIN
```

Cada organización imprime su ID para el comando siguiente. Las contraseñas deben
tener al menos 12 caracteres. No se crean cuentas o contraseñas predeterminadas.

Para pruebas **locales** sobre una Application DB vacía, `npm run agent:demo:login`
crea `demo.local@solvo.test` como CLIENT_USER con contraseña aleatoria. Sólo la
escribe en `apps/agent/var/local-login.txt`, con permisos0600 e ignorada por Git.
No modifica la clave de una cuenta existente. Eliminar la cuenta y el archivo al
dejar de usar la demo; no usar este atajo como provisión de usuarios de producción.

`User.catalog_demo_user_id` se resuelve desde el usuario autenticado y se inyecta
en el contexto de ejecución server-side. ADK identifica al usuario como
`app:<application-user-id>`, mientras los filtros reciben `demo-user-01` o
`demo-user-02`. El modelo no puede seleccionar identidad. Sin mapeo se rechaza
la operación de filtros. Este puente es temporal; debe eliminarse al autenticar
realmente Catalog API. Dos usuarios mapeados al mismo demo ID compartirían filtros
en Catalog API: asignar IDs distintos a clientes distintos durante la demo.

`FRONTEND_ORIGIN` configura un único origen explícito para CORS con credentials.
Las operaciones con Origin diferente se rechazan, incluido login, para proteger
las sesiones con cookies. No se usan tokens en localStorage. Auth falla cerrado.

Los endpoints antiguos `/attachments` y `/drafts` quedan deshabilitados por
defecto. `LEGACY_INTAKE_ENABLED=true` los habilita sólo para pruebas internas;
su header demo no constituye autorización. El producto usa las rutas
`/conversations/{id}/attachments` y `/conversations/{id}/drafts` autenticadas.
