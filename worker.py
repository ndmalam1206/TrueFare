import os

from flask import Response as FlaskResponse, request
from pyodide.ffi import run_sync
from workers import Response as WorkerResponse, wsgi

os.environ['TRUEFARE_WORKER'] = '1'

from app import app, ensure_schema


async def fetch_asset(assets, url):
    return await assets.fetch(url)


_schema_initialized = False


@app.before_request
def configure_cloudflare_request():
    global _schema_initialized

    bindings = request.environ['workers.env']
    if request.path.startswith('/static/'):
        assets = bindings.ASSETS
        asset_path = request.path.removeprefix('/static') or '/'
        response = WorkerResponse(run_sync(fetch_asset(assets, f'https://assets.local{asset_path}')))
        return FlaskResponse(
            run_sync(response.bytes()),
            status=response.status,
            headers={key: value for key, value in response.headers.items()},
        )

    database_url = getattr(bindings, 'DATABASE_URL', None)
    if not database_url:
        return FlaskResponse('The DATABASE_URL Worker variable is required.', status=503)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    secret_key = getattr(bindings, 'SECRET_KEY', None)
    if not secret_key:
        return FlaskResponse('The SECRET_KEY Worker secret is required.', status=503)
    app.config['SECRET_KEY'] = secret_key
    app.config['SESSION_COOKIE_SECURE'] = True
    if getattr(bindings, 'ADMIN_USERNAME', None):
        os.environ['ADMIN_USERNAME'] = bindings.ADMIN_USERNAME
    if getattr(bindings, 'ADMIN_PASSWORD', None):
        os.environ['ADMIN_PASSWORD'] = bindings.ADMIN_PASSWORD

    if not _schema_initialized:
        ensure_schema()
        _schema_initialized = True


Default = wsgi.entrypoint(app)
