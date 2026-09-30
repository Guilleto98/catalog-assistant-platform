"""Launch isolated API + real browser acceptance. Reuses authorized server-side key."""
import os
import sqlite3
from pathlib import Path
import secrets
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import urllib.request
from solvo_client_agent.config import get_settings

def main():
    workspace = Path(__file__).resolve().parents[3]
    with TemporaryDirectory(prefix='solvo-client-web-smoke-') as temp:
        os.environ['CATALOG_API_BASE_URL'] = 'http://localhost:3001/api/v1'
        get_settings()  # Loads the existing ignored .env without exposing it.
        if not os.getenv('OPENAI_API_KEY'):
            raise SystemExit('Se necesita la credencial del backend para el smoke real.')
        catalog_root = workspace / 'apps/catalog-api'
        catalog_env = dict(os.environ, DATABASE_URL=f'file:{temp}/catalog.db', PORT='3001')
        migration = catalog_root / 'prisma/migrations/20260928000000_init/migration.sql'
        with sqlite3.connect(Path(temp) / 'catalog.db') as db:
            db.executescript(migration.read_text())
        subprocess.run(['node', '-r', 'ts-node/register', 'prisma/seed.ts'],
            cwd=catalog_root, env=catalog_env, check=True, stdout=subprocess.DEVNULL)
        env = dict(os.environ, WEB_SMOKE_ROOT=temp, WEB_SMOKE_PASSWORD=secrets.token_urlsafe(24), WEB_SMOKE_PORT='3101')
        with open(Path(temp) / 'catalog.log', 'w') as catalog_log, open(Path(temp) / 'server.log', 'w') as log:
            catalog = subprocess.Popen(['node', 'dist/main.js'], cwd=catalog_root,
                env=catalog_env, stdout=catalog_log, stderr=catalog_log)
            server = subprocess.Popen([sys.executable, '-m', 'scripts.web_smoke_server'], env=env, stdout=log, stderr=log)
            try:
                for _ in range(120):
                    if catalog.poll() is not None:
                        raise RuntimeError('No se pudo iniciar el catálogo temporal.')
                    try:
                        with urllib.request.urlopen('http://localhost:3001/api/v1/health', timeout=1) as response:
                            if response.status == 200: break
                    except OSError: time.sleep(.25)
                else: raise RuntimeError('El catálogo temporal no respondió.')
                for _ in range(120):
                    if server.poll() is not None:
                        raise RuntimeError('No se pudo iniciar la API aislada. No se tocaron datos de usuarios.')
                    try:
                        with urllib.request.urlopen('http://localhost:3101/health', timeout=1) as response:
                            if response.status == 200: break
                    except OSError: time.sleep(.25)
                else: raise RuntimeError('La API aislada no respondió.')
                # Browser process never receives the provider credential.
                browser_env = {key: value for key, value in env.items() if key != 'OPENAI_API_KEY'}
                browser_env['WEB_SMOKE_PYTHON'] = sys.executable
                result = subprocess.run(['npx', 'playwright', 'test', '--config', 'playwright.config.ts'],
                    cwd=workspace / 'apps/web', env=browser_env)
                return result.returncode
            finally:
                server.terminate()
                try: server.wait(timeout=10)
                except subprocess.TimeoutExpired: server.kill(); server.wait()
                catalog.terminate()
                try: catalog.wait(timeout=10)
                except subprocess.TimeoutExpired: catalog.kill(); catalog.wait()

if __name__ == '__main__':
    raise SystemExit(main())
