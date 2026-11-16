"""Filesystem boundaries and SQLite metadata; document bodies remain ordinary files."""
import os
import sqlite3
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from fastapi import HTTPException

ROOT = Path(os.getenv('NEXOTEX_DATA', '/data')).resolve()
PROJECTS = Path(os.getenv('NEXOTEX_PROJECTS', '/workspace')).resolve()
MAX_FILE = int(os.getenv('NEXOTEX_MAX_FILE_MB', '10')) * 1024 * 1024

def init() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    PROJECTS.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, main TEXT NOT NULL DEFAULT "main.tex")')

def db() -> sqlite3.Connection:
    conn = sqlite3.connect(ROOT / 'metadata.sqlite3')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def project(project_id: str) -> Path:
    with db() as conn:
        row = conn.execute('SELECT id FROM projects WHERE id=?', (project_id,)).fetchone()
    if not row:
        raise HTTPException(404, 'Projeto não encontrado')
    return safe(PROJECTS, project_id)

def safe(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if not relative or candidate.is_absolute() or '\\' in relative or any(p in ('.', '..') for p in relative.split('/')):
        raise HTTPException(400, 'Caminho inválido')
    target = root / candidate
    # Reject symlinks even when they resolve inside the project.
    if any(p.is_symlink() for p in [target, *target.parents] if p != root.parent):
        raise HTTPException(400, 'Links simbólicos não são permitidos')
    if not target.resolve().is_relative_to(root.resolve()):
        raise HTTPException(400, 'Caminho fora do projeto')
    return target

def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.nexotex-')
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(content)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


_locks: dict[str, threading.RLock] = {}
_lock_guard = threading.Lock()

@contextmanager
def file_lock(path: Path):
    """Serialize application writes, including compare-and-insert transfers."""
    with _lock_guard:
        lock = _locks.setdefault(str(path.resolve()), threading.RLock())
    with lock:
        yield
