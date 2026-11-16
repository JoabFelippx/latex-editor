"""Real TeX integration: no mocked process or static PDF fixtures."""
import time
import pytest
from app.core import storage


def build(client,pid):
    assert client.post(f'/api/projects/{pid}/compile').status_code == 202
    deadline=time.monotonic()+150
    while time.monotonic()<deadline:
        response=client.get(f'/api/projects/{pid}/compile').json()
        if response['state'] not in ('queued','running'):
            return response
        time.sleep(.15)
    pytest.fail('Compilação não terminou')

def test_valid_invalid_preserves_pdf(client):
    pid=client.post('/api/projects',json={'name':'Teste real'}).json()['id']
    result=build(client,pid)
    assert result['state']=='success',result['log']
    pdf=client.get(f'/api/projects/{pid}/pdf').content
    assert pdf.startswith(b'%PDF-')
    client.put(f'/api/projects/{pid}/file',json={'path':'main.tex','content':r'\documentclass{article}\begin{document}\unknowncommand\end{document}'})
    result=build(client,pid)
    assert result['state']=='error'
    assert result['errors']
    assert client.get(f'/api/projects/{pid}/pdf').content == pdf

@pytest.mark.parametrize('document',[
    r'\documentclass{article}\begin{document}\input{chapters/intro}\end{document}',
    r'\documentclass{abntex2}\usepackage[utf8]{inputenc}\begin{document}\chapter{Introdução}Exemplo abnTeX2.\end{document}',
    r'\documentclass{abntex2}\usepackage[normalem]{ulem}\usepackage{soul}\begin{document}\chapter{Revisão}\uline{Trecho importante} e \sout{trecho removido}. \hl{Destaque}.\end{document}',
    r'\documentclass{article}\begin{document}Exemplo~\cite{knuth}.\bibliographystyle{plain}\bibliography{refs}\end{document}',
    r'\documentclass{article}\usepackage[backend=biber]{biblatex}\addbibresource{refs.bib}\begin{document}\cite{knuth}\printbibliography\end{document}',
])
def test_multifile_abntex_and_bibliographies(client,document):
    pid=client.post('/api/projects',json={'name':'Integração'}).json()['id']
    for path,content in [('main.tex',document),('chapters/intro.tex','Conteúdo incluído.'),('refs.bib','@book{knuth,author={Donald Knuth},title={The TeXbook},year={1984},publisher={Addison-Wesley}}')]:
        assert client.put(f'/api/projects/{pid}/file',json={'path':path,'content':content}).status_code == 200
    result=build(client,pid)
    assert result['state']=='success',result['log']

def test_tex_cannot_read_metadata(client):
    pid=client.post('/api/projects',json={'name':'Sandbox'}).json()['id']
    document=r'\documentclass{article}\begin{document}\input{/data/metadata.sqlite3}\end{document}'
    client.put(f'/api/projects/{pid}/file',json={'path':'main.tex','content':document})
    result=build(client,pid)
    assert result['state']=='error'
    assert 'no output PDF' in result['log'].lower() or 'not found' in result['log'].lower() or 'not reading' in result['log'].lower(),result['log']


def test_timeout(client,monkeypatch):
    monkeypatch.setenv('NEXOTEX_COMPILE_TIMEOUT','1')
    pid=client.post('/api/projects',json={'name':'Loop'}).json()['id']
    client.put(f'/api/projects/{pid}/file',json={'path':'main.tex','content':r'\documentclass{article}\begin{document}\loop\iftrue\repeat\end{document}'})
    result=build(client,pid)
    assert result['state']=='error'
    assert 'Tempo limite' in result['log']

def test_queue_coalesces_requests(client):
    pid=client.post('/api/projects',json={'name':'Fila'}).json()['id']
    for _ in range(4):
        assert client.post(f'/api/projects/{pid}/compile').status_code==202
    deadline=time.monotonic()+150
    while time.monotonic()<deadline:
        state=client.get(f'/api/projects/{pid}/compile').json()
        if state['state']=='success' and not state.get('pending'):
            break
        time.sleep(.15)
    else:
        pytest.fail('Fila não terminou')
    assert client.get(f'/api/projects/{pid}/pdf').content.startswith(b'%PDF-')
