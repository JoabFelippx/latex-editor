"""Real disk, SQLite and Pandoc integration; no converter mocks."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core import storage
from app.services import drafts


def project(client):
    return client.post('/api/projects', json={'name':'Rascunhos'}).json()['id']

def create(client,pid,path='rascunhos/introducao.md',content='# Introdução\n\nUm texto inicial.'):
    response=client.post(f'/api/projects/{pid}/drafts',json={'path':path,'content':content})
    assert response.status_code==201,response.text
    return response.json()

def read(client,pid,path):
    return client.get(f'/api/projects/{pid}/file',params={'path':path}).json()

def preview(client,pid,**changes):
    payload={'path':'rascunhos/introducao.md','destination':'main.tex','position':0,**changes}
    return client.post(f'/api/projects/{pid}/drafts/preview',json=payload)

def test_draft_files_metadata_and_restart(client):
    pid=project(client);create(client,pid)
    path='rascunhos/introducao.md'
    response=client.put(f'/api/projects/{pid}/file',json={'path':path,'content':'# Nova ideia\n\nUma hipótese científica.'})
    assert response.status_code==200
    note={'id':'one','kind':'question','color':'#ba8080','text':'Conferir esta hipótese','source_quote':'hipótese','pdf_path':None}
    meta={'title':'Hipótese','state':'review','linked_tex':'main.tex','section':'Introdução','references':['knuth'],'observations':[note]}
    assert client.put(f'/api/projects/{pid}/drafts/meta',params={'path':path},json=meta).status_code==200
    with TestClient(app) as restarted:
        assert read(restarted,pid,path)['content'].endswith('científica.')
        result=restarted.get(f'/api/projects/{pid}/drafts/meta',params={'path':path}).json()
        assert result['state']=='review' and result['observations'][0]['source_quote']=='hipótese'
        assert restarted.get(f'/api/projects/{pid}/drafts',params={'q':'científica'}).json()[0]['path']==path
    assert (storage.PROJECTS/pid/path).is_file()

def test_preview_cancellation_confirmation_and_replay(client):
    pid=project(client);create(client,pid,content='## Ideia\n\n**Forte** e *ênfase*. $E=mc^2$ [@knuth].\n\n- Um\n- Dois')
    original=read(client,pid,'main.tex')['content']
    response=preview(client,pid,position=original.index('\\end{document}'))
    assert response.status_code==200,response.text
    result=response.json();fragment=result['fragment']
    assert '\\subsection{Ideia}' in fragment
    assert '\\textbf{Forte}' in fragment and '\\emph' in fragment
    assert 'E=mc^2' in fragment and '\\cite{knuth}' in fragment
    assert '\\begin{itemize}' in fragment
    assert '\\documentclass' not in fragment and '\\tightlist' not in fragment
    assert read(client,pid,'main.tex')['content']==original  # Closing/cancelling does not mutate files.
    assert client.post(f'/api/projects/{pid}/drafts/apply',json={'token':result['token']}).status_code==400
    applied=client.post(f'/api/projects/{pid}/drafts/apply',json={'token':result['token'],'confirmed':True})
    assert applied.status_code==200,applied.text
    content=read(client,pid,'main.tex')['content'];assert content.startswith(original[:original.index('\\end{document}')])
    assert content.endswith(original[original.index('\\end{document}'):])
    assert read(client,pid,'rascunhos/introducao.md')['content'].startswith('## Ideia')
    assert client.get(f'/api/projects/{pid}/drafts/meta',params={'path':'rascunhos/introducao.md'}).json()['state']=='idea'
    assert client.post(f'/api/projects/{pid}/drafts/apply',json={'token':result['token'],'confirmed':True}).status_code==409
    assert (storage.ROOT/'transfer-backups'/pid/(result['token']+'.tex')).read_text()==original

def test_selection_unicode_and_citation_modes(client):
    pid=project(client);source='💡 Não enviar.\n\n## Hipótese\n\nTexto $\\alpha + \\beta$ e @knuth.\n\nNão enviar também.'
    create(client,pid,content=source)
    result=preview(client,pid,start=source.index('##'),end=source.index('\n\nNão enviar também'),citation_style='abntex2')
    assert result.status_code==200,result.text
    fragment=result.json()['fragment']
    assert 'Não enviar' not in fragment and '\\citeonline{knuth}' in fragment and '\\alpha + \\beta' in fragment

def test_invalid_selection_and_destination_do_not_change_source(client):
    pid=project(client);create(client,pid)
    original=read(client,pid,'main.tex')['content']
    for data in [{'start':2,'end':1},{'position':999999},{'destination':'../main.tex'}]:
        assert preview(client,pid,**data).status_code==400
    assert read(client,pid,'main.tex')['content']==original

def test_transfer_detects_concurrent_changes(client):
    pid=project(client);create(client,pid)
    for changed in ['main.tex','rascunhos/introducao.md']:
        result=preview(client,pid).json()
        current=read(client,pid,changed)['content']
        client.put(f'/api/projects/{pid}/file',json={'path':changed,'content':current+'\nMudou externamente.'})
        target=read(client,pid,'main.tex')['content']
        assert client.post(f'/api/projects/{pid}/drafts/apply',json={'token':result['token'],'confirmed':True}).status_code==409
        assert read(client,pid,'main.tex')['content']==target

def test_history_restore_preserves_latest_content(client):
    pid=project(client);path='rascunhos/introducao.md';create(client,pid,content='Versão inicial')
    client.post(f'/api/projects/{pid}/drafts/history',params={'path':path})
    client.put(f'/api/projects/{pid}/file',json={'path':path,'content':'Versão atual'})
    versions=client.get(f'/api/projects/{pid}/drafts/history',params={'path':path}).json()
    assert len(versions)==1
    file=read(client,pid,path)
    response=client.post(f'/api/projects/{pid}/drafts/restore',json={'path':path,'version_id':versions[0]['id'],'expected_hash':file['hash']})
    assert response.status_code==200,response.text
    assert read(client,pid,path)['content']=='Versão inicial'
    assert len(client.get(f'/api/projects/{pid}/drafts/history',params={'path':path}).json())==2

def test_move_folder_preserves_history_and_links(client):
    pid=project(client);path='rascunhos/introducao.md';meta=create(client,pid)
    client.post(f'/api/projects/{pid}/drafts/history',params={'path':path})
    client.put(f'/api/projects/{pid}/drafts/meta',params={'path':path},json={'title':'Intro','linked_tex':'main.tex'})
    assert client.post(f'/api/projects/{pid}/move',json={'source':'rascunhos','destination':'ideias'}).status_code==200
    assert client.post(f'/api/projects/{pid}/move',json={'source':'main.tex','destination':'capitulos/intro.tex'}).status_code==200
    changed=client.get(f'/api/projects/{pid}/drafts/meta',params={'path':'ideias/introducao.md'}).json()
    assert changed['id']==meta['id'] and changed['linked_tex']=='capitulos/intro.tex'
    assert len(client.get(f'/api/projects/{pid}/drafts/history',params={'path':'ideias/introducao.md'}).json())==1
    assert client.delete(f'/api/projects/{pid}').status_code==204
    with storage.db() as conn:assert conn.execute('SELECT count(*) FROM drafts').fetchone()[0]==0

def test_bibtex_entries_are_read_without_invented_metadata(client):
    pid=project(client)
    client.put(f'/api/projects/{pid}/file',json={'path':'refs.bib','content':'@book{knuth1984, author={Donald E. Knuth}, title={The TeXbook}, year={1984}, publisher={Addison-Wesley}}'})
    refs=client.get(f'/api/projects/{pid}/references')
    assert refs.status_code==200,refs.text
    entry=refs.json()[0];assert entry['key']=='knuth1984' and entry['title']=='The TeXbook' and 'Knuth' in entry['authors']

def test_draft_save_conflict_and_path_safety(client):
    pid=project(client);create(client,pid)
    file=read(client,pid,'rascunhos/introducao.md')
    assert client.put(f'/api/projects/{pid}/file',json={'path':'rascunhos/introducao.md','content':'Nova ideia','expected_hash':file['hash']}).status_code==200
    assert client.put(f'/api/projects/{pid}/file',json={'path':'rascunhos/introducao.md','content':'Sobrescrever','expected_hash':file['hash']}).status_code==409
    for path in ['../ideas.md','/tmp/ideas.md','ideas.tex']:
        assert client.post(f'/api/projects/{pid}/drafts',json={'path':path}).status_code==400

def test_drafts_are_not_automatically_included_in_tex(client):
    pid=project(client);original=read(client,pid,'main.tex')['content']
    create(client,pid,content='# Ideia que não deve ser compilada\n\\unknowncommand')
    assert read(client,pid,'main.tex')['content']==original


def test_converted_heading_compiles_in_existing_article(client):
    from test_compile import build
    pid=project(client);create(client,pid,content='# Seção integrada\n\nTexto **forte**, *ênfase* e $E=mc^2$.')
    original=read(client,pid,'main.tex')['content']
    result=preview(client,pid,position=original.index('\\end{document}')).json()
    assert '\\hypertarget' not in result['fragment']
    assert client.post(f'/api/projects/{pid}/drafts/apply',json={'token':result['token'],'confirmed':True}).status_code==200
    state=build(client,pid)
    assert state['state']=='success',state['log']
