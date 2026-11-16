from typing import Literal
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.core import storage as s
from app.services import drafts, conversion

router = APIRouter(prefix='/api/projects/{pid}')
class DraftInput(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    content: str = Field(default='', max_length=1048576)
    expected_hash: str | None = None
class Observation(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    kind: Literal['idea','reference','question','review','task'] = 'idea'
    color: str = Field(default='#d6b85e', pattern=r'^#[0-9a-fA-F]{6}$')
    text: str = Field(max_length=10000)
    quote: str = Field(default='', max_length=10000)
    source_quote: str = Field(default='', max_length=10000)
    pdf_path: str | None = Field(default=None, max_length=500)
    page: int | None = Field(default=None, ge=1, le=100000)
    ref_key: str = Field(default='', max_length=200)
class DraftMeta(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    state: Literal['idea','writing','review','integrated'] = 'idea'
    linked_tex: str | None = Field(default=None, max_length=500)
    section: str = Field(default='', max_length=300)
    references: list[str] = Field(default_factory=list, max_length=200)
    observations: list[Observation] = Field(default_factory=list, max_length=300)
class PreviewInput(BaseModel):
    path: str
    destination: str
    position: int = Field(ge=0)
    start: int | None = None
    end: int | None = None
    citation_style: Literal['auto','latex','abntex2','natbib','biblatex'] = 'auto'
class ApplyInput(BaseModel):
    token: str
    confirmed: bool = False
class RestoreInput(BaseModel):
    path: str
    version_id: str
    expected_hash: str

@router.get('/drafts')
def list_drafts(pid: str, q: str = ''):
    return drafts.list_drafts(pid, q[:500])

@router.post('/drafts', status_code=201)
def create(pid: str, body: DraftInput):
    drafts.save(pid, body.path, body.content, create=True)
    return drafts.ensure(pid, body.path)

@router.get('/drafts/meta')
def meta(pid: str, path: str):
    return drafts.ensure(pid, path)

@router.put('/drafts/meta')
def update(pid: str, path: str, body: DraftMeta):
    return drafts.update(pid, path, body.model_dump())

@router.get('/drafts/history')
def history(pid: str, path: str):
    return drafts.history(pid, path)

@router.post('/drafts/history')
def snapshot(pid: str, path: str):
    drafts.snapshot(pid, path)
    return drafts.history(pid, path)

@router.get('/drafts/version')
def version(pid: str, path: str, version_id: str):
    return drafts.version(pid, path, version_id)

@router.post('/drafts/restore')
def restore(pid: str, body: RestoreInput):
    content = drafts.version(pid, body.path, body.version_id)['content']
    file = drafts.target(pid, body.path)
    with s.file_lock(file):
        if drafts.digest(drafts.read(pid, body.path)) != body.expected_hash:
            raise HTTPException(409, 'Rascunho alterado. Reabra antes de restaurar.')
        drafts.snapshot(pid, body.path, 'before-restore')
        return drafts.save(pid, body.path, content, body.expected_hash)

@router.post('/drafts/preview')
def preview(pid: str, body: PreviewInput):
    return conversion.preview(pid, body.path, body.destination, body.position, body.start, body.end, body.citation_style)

@router.post('/drafts/apply')
def apply(pid: str, body: ApplyInput):
    return conversion.apply(pid, body.token, body.confirmed)

@router.get('/references')
def references(pid: str):
    return conversion.references(pid)

@router.get('/article')
def article(pid: str, path: str):
    file = s.safe(s.project(pid), path)
    if file.suffix.lower() != '.pdf' or not file.is_file():
        raise HTTPException(404, 'PDF não encontrado')
    with file.open('rb') as content:
        if content.read(5) != b'%PDF-':
            raise HTTPException(415, 'O arquivo não é um PDF válido')
    return FileResponse(file, media_type='application/pdf', headers={'Cache-Control': 'no-store'})
