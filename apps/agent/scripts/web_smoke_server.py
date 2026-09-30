"""Isolated real Application API for Angular acceptance tests, never production data."""
from contextlib import asynccontextmanager
from dataclasses import replace
import os
from pathlib import Path
import uvicorn
from solvo_client_agent.api.app import create_app
from solvo_client_agent.config import get_settings

root = Path(os.environ['WEB_SMOKE_ROOT'])
config = replace(get_settings(), application_database_path=root / 'application.db',
    adk_database_path=root / 'adk.db', intake_database_path=root / 'intake.db',
    attachment_storage_path=root / 'attachments', auth_cookie_secure=False,
    frontend_origin='http://localhost:4200', legacy_intake_enabled=False)
app = create_app(config)
original_lifespan = app.router.lifespan_context

@asynccontextmanager
async def lifespan(application):
    async with original_lifespan(application):
        org = application.state.platform.auth.create_organization('Prueba de frontend', 'web-smoke')
        application.state.platform.auth.create_user('web-smoke@example.test', os.environ['WEB_SMOKE_PASSWORD'],
            'CLIENT_USER', org.id, 'demo-user-01')
        yield

app.router.lifespan_context = lifespan
if __name__ == '__main__':
    uvicorn.run(app, host='127.0.0.1', port=int(os.getenv('WEB_SMOKE_PORT', '3101')), log_level='error', access_log=False)
