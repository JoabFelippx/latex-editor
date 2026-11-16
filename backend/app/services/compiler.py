"""One worker and one coalesced pending build per project, isolated with bubblewrap."""
import asyncio
import os
import re
import signal
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from fastapi import HTTPException
from app.core import storage as s

jobs: dict[str, dict] = {}
tasks: dict[str, asyncio.Task] = {}
semaphore = asyncio.Semaphore(2)

def status(pid: str) -> dict:
    s.project(pid)
    return jobs.get(pid, {'state': 'idle', 'log': '', 'errors': [], 'version': 0, 'pdf': (s.ROOT / 'builds' / pid / 'document.pdf').exists()})

def request(pid: str) -> dict:
    s.project(pid)
    if pid in tasks:
        jobs[pid]['pending'] = True
    else:
        jobs[pid] = {**status(pid), 'state': 'queued', 'pending': False}
        tasks[pid] = asyncio.create_task(run(pid))
    return status(pid)

async def run(pid: str) -> None:
    try:
        while True:
            jobs[pid].update(state='queued', pending=False)
            async with semaphore:
                await build(pid)
            if not jobs[pid]['pending']:
                break
    except Exception as exc:
        jobs[pid].update(state='error', log=f'Falha de infraestrutura: {exc}')
    finally:
        tasks.pop(pid, None)

def command(work: Path, main: str, output: str) -> list[str]:
    # Never expose the application, metadata or other projects to TeX.
    args = ['bwrap', '--die-with-parent', '--unshare-all', '--new-session', '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin', '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib64', '/lib64', '--ro-bind', '/etc/alternatives', '/etc/alternatives', '--ro-bind', '/etc/texmf', '/etc/texmf', '--ro-bind', '/var/lib/texmf', '/var/lib/texmf', '--dev', '/dev', '--tmpfs', '/tmp', '--bind', str(work), '/work', '--chdir', '/work', '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'HOME', '/tmp', '--setenv', 'openin_any', 'p', '--setenv', 'openout_any', 'p', '--', 'prlimit', '--cpu=90', '--as=1073741824', '--fsize=52428800', '--nproc=64', '--', 'latexmk', '-norc', '-pdf', '-synctex=1', '-interaction=nonstopmode', '-halt-on-error', '-file-line-error', '-no-shell-escape', '-outdir=' + output, './' + main]
    return args

async def build(pid: str) -> None:
    state = jobs[pid]
    state.update(state='running', log='', errors=[])
    with s.db() as conn:
        main = conn.execute('SELECT main FROM projects WHERE id=?', (pid,)).fetchone()['main']
    root = s.project(pid)
    s.safe(root, main)
    with tempfile.TemporaryDirectory(prefix='nexotex-') as temp:
        work = Path(temp)
        total = 0
        for source in root.rglob('*'):
            if source.is_symlink():
                raise RuntimeError('Projeto contém link simbólico')
            if source.is_file():
                total += source.stat().st_size
                if total > 100 * 1024 * 1024:
                    raise RuntimeError('Projeto excede 100 MB')
                dest = work / source.relative_to(root)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)
        if not (work / main).is_file():
            raise RuntimeError('Arquivo principal não encontrado')
        output = work / ('.nexotex-output-' + uuid.uuid4().hex)
        output.mkdir()
        with (work / 'process.log').open('wb') as log:
            proc = await asyncio.create_subprocess_exec(*command(work, main, output.name), stdout=log, stderr=asyncio.subprocess.STDOUT, start_new_session=True)
            try:
                await asyncio.wait_for(proc.wait(), timeout=int(os.getenv('NEXOTEX_COMPILE_TIMEOUT', '120')))
            except (asyncio.TimeoutError, asyncio.CancelledError) as exc:
                os.killpg(proc.pid, signal.SIGKILL)
                await proc.wait()
                if isinstance(exc, asyncio.CancelledError):
                    raise
                state['log'] = 'Tempo limite de compilação excedido.\n'
        state['log'] += (work / 'process.log').read_text(errors='replace')[-500000:]
        state['errors'] = [{'path': m[0].removeprefix('./'), 'line': int(m[1]), 'message': m[2]} for m in re.findall(r'(?:^|\n)([^\n:]+\.tex):(\d+):\s*(.*)', state['log'])]
        pdf = output / (Path(main).stem + '.pdf')
        success = proc.returncode == 0 and pdf.is_file()
        if success:
            s.atomic_write(s.ROOT / 'builds' / pid / 'document.pdf', pdf.read_bytes())
            state['version'] = time.time_ns()
        state.update(state='success' if success else 'error', pdf=(s.ROOT / 'builds' / pid / 'document.pdf').exists())
