import asyncio
import io
import shutil
import sqlite3
import tempfile
import zipfile
from starlette.background import BackgroundTask
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from app.core import storage as s
from app.services import projects, compiler, drafts

router = APIRouter(prefix='/api')
class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=120, pattern=r'\S')
class ProjectUpdate(ProjectInput):
    main: str = Field(min_length=1, max_length=500)
class FileInput(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = ''
    directory: bool = False
    expected_hash: str | None = None
class MoveInput(BaseModel):
    source: str
    destination: str

@router.get('/health')
def health():
    return {'status': 'ok'}

@router.get('/projects')
def list_projects():
    with s.db() as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM projects ORDER BY name')]

@router.post('/projects', status_code=201)
def create_project(body: ProjectInput):
    return projects.create(body.name)

@router.put('/projects/{pid}')
def update_project(pid: str, body: ProjectUpdate):
    root = s.project(pid)
    if not body.main.endswith('.tex') or not s.safe(root, body.main).is_file():
        raise HTTPException(400, 'Escolha um arquivo .tex existente')
    with s.db() as conn:
        conn.execute('UPDATE projects SET name=?, main=? WHERE id=?', (body.name, body.main, pid))
    return {'id': pid, **body.model_dump()}

@router.delete('/projects/{pid}', status_code=204)
def delete_project(pid: str):
    root = s.project(pid)
    if pid in compiler.tasks:
        raise HTTPException(409, 'Aguarde a compilação terminar')
    shutil.rmtree(root)
    shutil.rmtree(s.ROOT / 'builds' / pid, ignore_errors=True)
    with s.db() as conn:
        conn.execute('DELETE FROM projects WHERE id=?', (pid,))
    compiler.jobs.pop(pid, None)

@router.get('/projects/{pid}/files')
def list_files(pid: str):
    return projects.tree(pid)

@router.get('/projects/{pid}/file')
def read_file(pid: str, path: str):
    target = s.safe(s.project(pid), path)
    if not target.is_file():
        raise HTTPException(404, 'Arquivo não encontrado')
    if target.stat().st_size > s.MAX_FILE:
        raise HTTPException(413, 'Arquivo muito grande para o editor')
    try:
        content = target.read_text(encoding='utf-8')
        return {'content': content, 'hash': drafts.digest(content)}
    except UnicodeError as exc:
        raise HTTPException(415, 'Arquivo binário: use upload ou exportação') from exc

@router.put('/projects/{pid}/file')
def write_file(pid: str, body: FileInput):
    target = s.safe(s.project(pid), body.path)
    data = body.content.encode()
    if len(data) > s.MAX_FILE:
        raise HTTPException(413, 'Arquivo excede o limite')
    if body.directory:
        target.mkdir(parents=True, exist_ok=True)
    else:
        if target.suffix.lower() == '.md':
            return drafts.save(pid, body.path, body.content, body.expected_hash)
        with s.file_lock(target):
            if body.expected_hash is not None and (not target.is_file() or drafts.digest(target.read_text('utf-8')) != body.expected_hash):
                raise HTTPException(409, 'O arquivo mudou no disco. Reabra antes de salvar.')
            s.atomic_write(target, data)
    return {'saved': True, 'hash': drafts.digest(body.content)}

@router.post('/projects/{pid}/move')
def move_file(pid: str, body: MoveInput):
    root = s.project(pid)
    src, dst = s.safe(root, body.source), s.safe(root, body.destination)
    if not src.exists():
        raise HTTPException(404, 'Origem não encontrada')
    if dst.exists():
        raise HTTPException(409, 'Destino já existe')
    dst.parent.mkdir(parents=True, exist_ok=True)
    src.rename(dst)
    drafts.moved(pid, body.source, body.destination)
    return {'moved': True}

@router.delete('/projects/{pid}/file', status_code=204)
def delete_file(pid: str, path: str):
    target = s.safe(s.project(pid), path)
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink(missing_ok=True)
    drafts.deleted(pid, path)

@router.post('/projects/{pid}/upload')
async def upload(pid: str, file: UploadFile, path: str):
    target = s.safe(s.project(pid), path)
    data = await file.read(s.MAX_FILE + 1)
    if len(data) > s.MAX_FILE:
        raise HTTPException(413, 'Upload muito grande')
    s.atomic_write(target, data)
    return {'saved': True}

@router.get('/projects/{pid}/export')
def export(pid: str):
    return Response(projects.archive(pid), media_type='application/zip', headers={'Content-Disposition': 'attachment; filename="projeto.zip"'})

@router.post('/import', status_code=201)
async def import_project(file: UploadFile):
    data = await file.read(25 * 1024 * 1024 + 1)
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, 'ZIP excede 25 MB')
    return projects.import_zip(data, Path(file.filename or 'Projeto').stem[:120])

@router.post('/projects/{pid}/compile', status_code=202)
async def compile_project(pid: str):
    return compiler.request(pid)

@router.get('/projects/{pid}/compile')
async def compile_status(pid: str):
    return compiler.status(pid)

@router.get('/projects/{pid}/pdf')
def pdf(pid: str):
    s.project(pid)
    target = s.ROOT / 'builds' / pid / 'document.pdf'
    if not target.exists():
        raise HTTPException(404, 'Compile o projeto para gerar o PDF')
    return FileResponse(target, media_type='application/pdf', headers={'Cache-Control': 'no-store'})


@router.get('/backup')
def backup():
    """SQLite backup API makes a consistent metadata snapshot without stopping readers."""
    temp = tempfile.TemporaryDirectory(prefix='nexotex-backup-')
    root = Path(temp.name)
    try:
        with s.db() as source, sqlite3.connect(root / 'metadata.sqlite3') as dest:
            source.backup(dest)
        with zipfile.ZipFile(root / 'backup.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.write(root / 'metadata.sqlite3', 'data/metadata.sqlite3')
            with s.db() as conn:
                ids = [row['id'] for row in conn.execute('SELECT id FROM projects')]
            for pid in ids:
                project_root = s.project(pid)
                for entry in projects.tree(pid):
                    if not entry['directory']:
                        archive.write(s.safe(project_root, entry['path']), f"workspace/{pid}/{entry['path']}")
        return FileResponse(root / 'backup.zip', filename='nexotex-backup.zip', background=BackgroundTask(temp.cleanup))
    except Exception:
        temp.cleanup()
        raise
