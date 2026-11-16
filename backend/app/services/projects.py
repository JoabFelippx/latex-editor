import io
import shutil
import stat
import uuid
import zipfile
from fastapi import HTTPException
from app.core import storage as s

TEMPLATE = r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[brazil]{babel}
\usepackage{amsmath,graphicx}
\title{Meu projeto no NexoTeX}
\author{Seu nome}
\date{\today}
\begin{document}
\maketitle
\section{Introdução}
Uma ideia ganha forma quando começamos a escrever.
\end{document}
"""

def create(name: str, template: bool = True) -> dict:
    pid = uuid.uuid4().hex
    root = s.PROJECTS / pid
    root.mkdir()
    if template:
        s.atomic_write(root / 'main.tex', TEMPLATE.encode())
    with s.db() as conn:
        conn.execute('INSERT INTO projects(id,name) VALUES (?,?)', (pid, name))
    return {'id': pid, 'name': name, 'main': 'main.tex'}

def tree(pid: str) -> list[dict]:
    root = s.project(pid)
    return [{'path': p.relative_to(root).as_posix(), 'directory': p.is_dir()} for p in sorted(root.rglob('*')) if not p.is_symlink() and not any(x.startswith('.') for x in p.relative_to(root).parts)]

def archive(pid: str) -> bytes:
    root = s.project(pid)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as archive:
        for item in tree(pid):
            if not item['directory']:
                archive.write(s.safe(root, item['path']), item['path'])
    return buf.getvalue()

def import_zip(data: bytes, name: str) -> dict:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            items = archive.infolist()
            if len(items) > 2000 or sum(x.file_size for x in items) > 100 * 1024 * 1024:
                raise HTTPException(413, 'ZIP excede 100 MB descompactados ou 2000 entradas')
            for item in items:
                s.safe(s.PROJECTS, item.filename.rstrip('/'))
                if stat.S_ISLNK(item.external_attr >> 16) or item.flag_bits & 1:
                    raise HTTPException(400, 'ZIP com links ou criptografia não permitido')
            project = create(name, False)
            root = s.project(project['id'])
            try:
                for item in items:
                    dest = s.safe(root, item.filename.rstrip('/'))
                    if item.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                    else:
                        s.atomic_write(dest, archive.read(item))
                tex = sorted(root.rglob('*.tex'))
                main = 'main.tex' if (root / 'main.tex').exists() else (tex[0].relative_to(root).as_posix() if tex else 'main.tex')
                with s.db() as conn:
                    conn.execute('UPDATE projects SET main=? WHERE id=?', (main, project['id']))
                return {**project, 'main': main}
            except Exception:
                shutil.rmtree(root)
                with s.db() as conn:
                    conn.execute('DELETE FROM projects WHERE id=?', (project['id'],))
                raise
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise HTTPException(400, 'ZIP inválido') from exc
