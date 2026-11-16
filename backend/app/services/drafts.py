"""Markdown stays on disk; supplementary metadata and bounded history stay in SQLite."""
import hashlib
import json
import time
import uuid
from pathlib import Path
from fastapi import HTTPException
from app.core import storage as s

STATES = ('idea', 'writing', 'review', 'integrated')
MAX_DRAFT = 1024 * 1024

def init() -> None:
    with s.db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS drafts (
          id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
          path TEXT NOT NULL, title TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'idea',
          linked_tex TEXT, section TEXT NOT NULL DEFAULT '', references_json TEXT NOT NULL DEFAULT '[]',
          observations_json TEXT NOT NULL DEFAULT '[]', created_at REAL NOT NULL, modified_at REAL NOT NULL,
          UNIQUE(project_id,path));
        CREATE TABLE IF NOT EXISTS draft_versions (
          id TEXT PRIMARY KEY, draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
          created_at REAL NOT NULL, reason TEXT NOT NULL, content TEXT NOT NULL, digest TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS draft_transfers (
          token TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
          source_path TEXT NOT NULL, source_hash TEXT NOT NULL, target_path TEXT NOT NULL,
          target_hash TEXT NOT NULL, position INTEGER NOT NULL, fragment TEXT NOT NULL,
          created_at REAL NOT NULL, applied INTEGER NOT NULL DEFAULT 0);
        ''')

def digest(content: str) -> str:
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def target(pid: str, path: str) -> Path:
    result = s.safe(s.project(pid), path)
    if result.suffix.lower() != '.md':
        raise HTTPException(400, 'Rascunhos devem usar extensão .md')
    return result

def read(pid: str, path: str) -> str:
    file = target(pid, path)
    if not file.is_file():
        raise HTTPException(404, 'Rascunho não encontrado')
    if file.stat().st_size > MAX_DRAFT:
        raise HTTPException(413, 'Rascunho excede 1 MB')
    try:
        return file.read_text('utf-8')
    except UnicodeError as exc:
        raise HTTPException(415, 'Rascunho precisa usar UTF-8') from exc

def ensure(pid: str, path: str) -> dict:
    file = target(pid, path)
    if not file.is_file():
        raise HTTPException(404, 'Rascunho não encontrado')
    now = time.time()
    with s.db() as conn:
        conn.execute('INSERT OR IGNORE INTO drafts(id,project_id,path,title,created_at,modified_at) VALUES(?,?,?,?,?,?)',
                     (uuid.uuid4().hex, pid, path, file.stem, now, file.stat().st_mtime))
        row = dict(conn.execute('SELECT * FROM drafts WHERE project_id=? AND path=?', (pid, path)).fetchone())
    for name in ('references', 'observations'):
        row[name] = json.loads(row.pop(name + '_json'))
    return row

def list_drafts(pid: str, query: str = '') -> list[dict]:
    root = s.project(pid)
    rows = []
    for file in sorted(root.rglob('*.md')):
        if file.is_symlink() or any(part.startswith('.') for part in file.relative_to(root).parts):
            continue
        path = file.relative_to(root).as_posix()
        meta = ensure(pid, path)
        if query and query.casefold() not in (meta['title'] + '\n' + path + '\n' + read(pid, path)).casefold():
            continue
        rows.append(meta)
    return rows

def snapshot(pid: str, path: str, reason: str = 'manual', content: str | None = None) -> None:
    meta = ensure(pid, path)
    content = read(pid, path) if content is None else content
    hash_value = digest(content)
    with s.db() as conn:
        latest = conn.execute('SELECT digest,created_at FROM draft_versions WHERE draft_id=? ORDER BY created_at DESC LIMIT 1', (meta['id'],)).fetchone()
        if latest and (latest['digest'] == hash_value or (reason == 'auto' and time.time() - latest['created_at'] < 300)):
            return
        conn.execute('INSERT INTO draft_versions VALUES(?,?,?,?,?,?)',
                     (uuid.uuid4().hex, meta['id'], time.time(), reason, content, hash_value))
        conn.execute('DELETE FROM draft_versions WHERE draft_id=? AND id NOT IN (SELECT id FROM draft_versions WHERE draft_id=? ORDER BY created_at DESC LIMIT 50)', (meta['id'], meta['id']))

def save(pid: str, path: str, content: str, expected_hash: str | None = None, create: bool = False) -> dict:
    file = target(pid, path)
    if len(content.encode()) > MAX_DRAFT:
        raise HTTPException(413, 'Rascunho excede 1 MB')
    with s.file_lock(file):
        if create and file.exists():
            raise HTTPException(409, 'Este caminho já existe')
        if file.exists():
            previous = read(pid, path)
            if expected_hash is not None and digest(previous) != expected_hash:
                raise HTTPException(409, 'O rascunho mudou no disco. Suas alterações locais foram preservadas; reabra para reconciliar.')
            if previous != content:
                snapshot(pid, path, 'auto', previous)
        elif expected_hash is not None:
            raise HTTPException(409, 'O rascunho foi removido ou movido')
        s.atomic_write(file, content.encode())
        meta = ensure(pid, path)
        with s.db() as conn:
            conn.execute('UPDATE drafts SET modified_at=? WHERE id=?', (time.time(), meta['id']))
        return {'saved': True, 'hash': digest(content)}

def update(pid: str, path: str, values: dict) -> dict:
    meta = ensure(pid, path)
    if values.get('linked_tex'):
        file = s.safe(s.project(pid), values['linked_tex'])
        if file.suffix != '.tex' or not file.is_file():
            raise HTTPException(400, 'Vincule um arquivo .tex existente')
    columns = {'title': 'title', 'state': 'state', 'linked_tex': 'linked_tex', 'section': 'section',
               'references': 'references_json', 'observations': 'observations_json'}
    for observation in values.get('observations', []):
        article = observation.get('pdf_path')
        if article:
            file = s.safe(s.project(pid), article)
            if file.suffix.lower() != '.pdf' or not file.is_file():
                raise HTTPException(400, 'Artigo PDF não encontrado')
    with s.db() as conn:
        for key, value in values.items():
            if key in columns:
                if key in ('references', 'observations'):
                    value = json.dumps(value, ensure_ascii=False)
                conn.execute(f'UPDATE drafts SET {columns[key]}=? WHERE id=?', (value, meta['id']))
    return ensure(pid, path)

def moved(pid: str, source: str, destination: str) -> None:
    with s.db() as conn:
        for row in conn.execute('SELECT id,path,linked_tex FROM drafts WHERE project_id=?', (pid,)).fetchall():
            for column in ('path', 'linked_tex'):
                old = row[column]
                if old and (old == source or old.startswith(source + '/')):
                    conn.execute(f'UPDATE drafts SET {column}=? WHERE id=?', (destination + old[len(source):], row['id']))

def deleted(pid: str, path: str) -> None:
    with s.db() as conn:
        for row in conn.execute('SELECT id,path,linked_tex FROM drafts WHERE project_id=?', (pid,)).fetchall():
            if row['path'] == path or row['path'].startswith(path + '/'):
                conn.execute('DELETE FROM drafts WHERE id=?', (row['id'],))
            elif row['linked_tex'] and (row['linked_tex'] == path or row['linked_tex'].startswith(path + '/')):
                conn.execute('UPDATE drafts SET linked_tex=NULL WHERE id=?', (row['id'],))

def history(pid: str, path: str) -> list[dict]:
    meta = ensure(pid, path)
    with s.db() as conn:
        return [dict(r) for r in conn.execute('SELECT id,created_at,reason,digest FROM draft_versions WHERE draft_id=? ORDER BY created_at DESC', (meta['id'],))]

def version(pid: str, path: str, version_id: str) -> dict:
    meta = ensure(pid, path)
    with s.db() as conn:
        row = conn.execute('SELECT * FROM draft_versions WHERE id=? AND draft_id=?', (version_id, meta['id'])).fetchone()
    if not row:
        raise HTTPException(404, 'Versão não encontrada')
    return dict(row)
