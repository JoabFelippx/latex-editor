"""Pandoc parses Markdown into an AST. Transfers are previewed, hashed and insert-only."""
import json
import re
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from fastapi import HTTPException
from app.core import storage as s
from app.services import drafts

FORMAT = 'markdown+tex_math_dollars+citations+task_lists+raw_tex-auto_identifiers'

def pandoc(content: str, source: str, destination: str) -> str:
    if len(content.encode()) > drafts.MAX_DRAFT:
        raise HTTPException(413, 'Conteúdo excede 1 MB')
    try:
        with tempfile.TemporaryDirectory(prefix='nexotex-pandoc-') as work:
            proc = subprocess.run(['prlimit', '--as=1073741824', '--cpu=10', '--', 'pandoc', '--sandbox',
                                   '--from', source, '--to', destination, '--wrap=none', '--no-highlight'], input=content,
                                  capture_output=True, text=True, timeout=15, cwd=work,
                                  env={'PATH': '/usr/bin:/bin', 'HOME': work, 'LANG': 'C.UTF-8'})
    except FileNotFoundError as exc:
        raise HTTPException(503, 'Pandoc não está instalado na imagem. Reconstrua o container.') from exc
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(422, 'A conversão excedeu o tempo permitido') from exc
    if proc.returncode:
        raise HTTPException(422, 'Pandoc não conseguiu converter: ' + proc.stderr[-1500:])
    return proc.stdout

def references(pid: str) -> list[dict]:
    root = s.project(pid)
    entries = []
    for file in sorted(root.rglob('*.bib')):
        path = file.relative_to(root).as_posix()
        s.safe(root, path)
        if file.stat().st_size > drafts.MAX_DRAFT:
            continue
        try:
            parsed = json.loads(pandoc(file.read_text('utf-8'), 'biblatex', 'csljson'))
        except (HTTPException, UnicodeError):
            continue
        for entry in parsed:
            authors = ', '.join(' '.join(str(a.get(k, '')) for k in ('given', 'family', 'literal')).strip() for a in entry.get('author', []))
            entries.append({'key': entry['id'], 'title': str(entry.get('title', '')), 'authors': authors, 'path': path})
    return entries

def citation_style(pid: str) -> str:
    root = s.project(pid)
    with s.db() as conn:
        main = conn.execute('SELECT main FROM projects WHERE id=?', (pid,)).fetchone()['main']
    # Inspect only local configuration; never interpret document commands here.
    files = [s.safe(root, main), *root.glob('*.cls')]
    text = '\n'.join(p.read_text(errors='replace')[:200000] for p in files if p.is_file() and not p.is_symlink())
    if 'abntex2' in text or 'abntex2cite' in text:
        return 'abntex2'
    if 'biblatex' in text:
        return 'biblatex'
    if 'natbib' in text:
        return 'natbib'
    return 'latex'

def convert(content: str, style: str = 'latex') -> tuple[str, list[str]]:
    ast = json.loads(pandoc(content, FORMAT, 'json'))
    warnings = []
    def render_inlines(inlines: list) -> str:
        if not inlines:
            return ''
        document = {**ast, 'blocks': [{'t': 'Plain', 'c': inlines}]}
        return pandoc(json.dumps(document), 'json', 'latex').strip()
    def walk(node):
        if isinstance(node, list):
            return [walk(x) for x in node]
        if not isinstance(node, dict):
            return node
        if node.get('t') == 'Cite':
            commands = []
            for cite in node['c'][0]:
                key = cite['citationId']
                if not re.fullmatch(r'[\w:./+\-]+', key):
                    raise HTTPException(422, 'Chave bibliográfica incompatível com inserção segura: ' + key)
                mode = cite['citationMode']['t']
                if style == 'abntex2':
                    cmd = {'AuthorInText': 'citeonline', 'SuppressAuthor': 'citeyear'}.get(mode, 'cite')
                elif style == 'natbib':
                    cmd = {'AuthorInText': 'citet', 'SuppressAuthor': 'citeyearpar'}.get(mode, 'citep')
                elif style == 'biblatex':
                    cmd = {'AuthorInText': 'textcite', 'SuppressAuthor': 'citeyear'}.get(mode, 'autocite')
                else:
                    cmd = 'cite'
                prefix = render_inlines(cite.get('citationPrefix', []))
                suffix = render_inlines(cite.get('citationSuffix', []))
                commands.append((prefix + ' ' if prefix else '') + '\\' + cmd + ('[' + suffix + ']' if suffix else '') + '{' + key + '}')
            return {'t': 'RawInline', 'c': ['latex', '; '.join(commands)]}
        if node.get('t') == 'Header' and node['c'][1][0]:
            warnings.append('Títulos com identificadores explícitos exigem hyperref no destino.')
        if node.get('t') == 'Table':
            warnings.append('Tabelas podem exigir longtable, booktabs e array no preâmbulo.')
        if node.get('t') == 'Link':
            url = node['c'][-1][0]
            if url.startswith('/nexotex/'):
                warnings.append('Links internos de pesquisa ficam como texto no LaTeX; confira a referência antes de integrar.')
                return {'t': 'Span', 'c': [['', [], []], walk(node['c'][1])]}
            warnings.append('Links externos exigem hyperref no documento de destino.')
        if node.get('t') == 'Image':
            warnings.append('Confira caminhos das imagens e carregue graphicx no preâmbulo.')
        return {k: walk(v) for k, v in node.items()}
    ast = walk(ast)
    fragment = pandoc(json.dumps(ast), 'json', 'latex')
    # Pandoc emits this helper for tight lists; remove the helper so inserted fragments
    # do not depend on a generated standalone preamble. Environments remain intact.
    fragment = fragment.replace('\\tightlist\n', '')
    if '\\square' in fragment or '\\boxtimes' in fragment:
        warnings.append('Checklists podem exigir amssymb; o estado dos itens é preservado.')
    if '\\begin{Shaded}' in fragment or '\\NormalTok' in fragment:
        warnings.append('Blocos de código com realce podem exigir macros de destaque no preâmbulo.')
    return fragment, sorted(set(warnings))

def preview(pid: str, path: str, destination: str, position: int, start: int | None, end: int | None, style: str) -> dict:
    source = drafts.read(pid, path)
    target = s.safe(s.project(pid), destination)
    if target.suffix != '.tex' or not target.is_file():
        raise HTTPException(400, 'Escolha um arquivo .tex existente')
    if target.stat().st_size > s.MAX_FILE:
        raise HTTPException(413, 'Destino muito grande')
    original = target.read_text('utf-8')
    if position < 0 or position > len(original):
        raise HTTPException(400, 'Posição de inserção inválida')
    if start is None and end is None:
        selected = source
    elif start is None or end is None or not 0 <= start < end <= len(source):
        raise HTTPException(400, 'Seleção inválida')
    else:
        selected = source[start:end]
    fragment, warnings = convert(selected, citation_style(pid) if style == 'auto' else style)
    if not fragment.strip():
        raise HTTPException(422, 'O trecho selecionado não contém conteúdo convertível')
    token = uuid.uuid4().hex
    with s.db() as conn:
        conn.execute('DELETE FROM draft_transfers WHERE created_at<?', (time.time() - 1800,))
        conn.execute('INSERT INTO draft_transfers VALUES(?,?,?,?,?,?,?,?,?,0)',
                     (token, pid, path, drafts.digest(source), destination, drafts.digest(original), position, fragment, time.time()))
    return {'token': token, 'fragment': fragment, 'warnings': warnings, 'position': position,
            'before': original[max(0, position-180):position], 'after': original[position:position+180]}

def apply(pid: str, token: str, confirmed: bool) -> dict:
    s.project(pid)
    if not confirmed:
        raise HTTPException(400, 'A inserção exige confirmação explícita')
    with s.db() as conn:
        row = conn.execute('SELECT * FROM draft_transfers WHERE token=? AND project_id=?', (token, pid)).fetchone()
    if not row or row['applied'] or time.time() - row['created_at'] > 1800:
        raise HTTPException(409, 'Prévia expirada ou já utilizada. Gere uma nova prévia.')
    target = s.safe(s.project(pid), row['target_path'])
    with s.file_lock(target):
        source = drafts.read(pid, row['source_path'])
        if not target.is_file():
            raise HTTPException(409, 'Destino removido. Gere uma nova prévia.')
        original = target.read_text('utf-8')
        if drafts.digest(original) != row['target_hash'] or drafts.digest(source) != row['source_hash']:
            raise HTTPException(409, 'O rascunho ou destino mudou. Nenhum conteúdo foi inserido; gere uma nova prévia.')
        # Mark token inside the same writer transaction; concurrent confirmations cannot replay it.
        with s.db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            used = conn.execute('SELECT applied FROM draft_transfers WHERE token=?', (token,)).fetchone()
            if used['applied']:
                raise HTTPException(409, 'Essa prévia já foi utilizada')
            position = row['position']
            insertion = '\n' + row['fragment'].rstrip() + '\n'
            content = original[:position] + insertion + original[position:]
            if len(content.encode()) > s.MAX_FILE:
                raise HTTPException(413, 'A inserção excederia o limite do arquivo')
            # Keep a durable copy of the exact target before insertion for recovery.
            backup = s.ROOT / 'transfer-backups' / pid / (token + '.tex')
            s.atomic_write(backup, original.encode())
            s.atomic_write(target, content.encode())
            conn.execute('UPDATE draft_transfers SET applied=1 WHERE token=?', (token,))
    drafts.snapshot(pid, row['source_path'], 'integration')
    return {'path': row['target_path'], 'content': content, 'hash': drafts.digest(content), 'position': position, 'inserted': len(insertion)}
