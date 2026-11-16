import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.api.routes import router
from app.api.drafts import router as drafts_router
from app.services import drafts
from app.core import storage
from app.services import compiler

@asynccontextmanager
async def lifespan(app):
    storage.init()
    drafts.init()
    yield
    tasks = list(compiler.tasks.values())
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

app = FastAPI(title='NexoTeX', lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost', '127.0.0.1', 'testserver'])

@app.middleware('http')
async def local_only(request: Request, call_next):
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        return JSONResponse({'detail': 'Origem não permitida'}, status_code=403)
    length = request.headers.get('content-length', '0')
    if length.isdigit() and int(length) > 27 * 1024 * 1024:
        return JSONResponse({'detail': 'Requisição muito grande'}, status_code=413)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response

@app.exception_handler(OSError)
async def filesystem_error(request, exc):
    return JSONResponse({'detail': 'Falha no acesso ao disco. Verifique caminhos, permissões e espaço disponível.'}, status_code=409)

app.include_router(router)
app.include_router(drafts_router)
static = Path(os.getenv('NEXOTEX_STATIC', '/app/static'))
if static.is_dir():
    app.mount('/', StaticFiles(directory=static, html=True), name='frontend')
