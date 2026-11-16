import io
import zipfile
from fastapi.testclient import TestClient
from app.main import app
from app.core import storage

def create(client):
    response = client.post('/api/projects', json={'name':'TCC'})
    assert response.status_code == 201
    return response.json()['id']

def test_files_persist_after_service_restart(client):
    pid = create(client)
    data = {'path':'capitulos/intro.tex','content':'Uma introdução acadêmica.'}
    assert client.put(f'/api/projects/{pid}/file', json=data).status_code == 200
    with TestClient(app) as restarted:
        assert restarted.get(f'/api/projects/{pid}/file',params={'path':data['path']}).json()['content'] == data['content']
        assert restarted.get('/api/projects').json()[0]['name'] == 'TCC'
    assert (storage.PROJECTS / pid / data['path']).read_text() == data['content']

def test_traversal_and_symlink(client):
    pid = create(client)
    for path in ['../evil','/etc/passwd','a/../../evil','a\\evil','.','a/./x']:
        assert client.put(f'/api/projects/{pid}/file',json={'path':path,'content':'x'}).status_code == 400
    (storage.PROJECTS / pid / 'link').symlink_to('/etc/passwd')
    assert client.get(f'/api/projects/{pid}/file',params={'path':'link'}).status_code == 400

def zip_data(entries):
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as archive:
        for name,content in entries.items():
            archive.writestr(name,content)
    return data.getvalue()

def test_zip_roundtrip_and_backup(client):
    response=client.post('/api/import',files={'file':('project.zip',zip_data({'main.tex':'Example','chapters/a.tex':'Chapter'}),'application/zip')})
    assert response.status_code == 201
    pid=response.json()['id']
    exported=client.get(f'/api/projects/{pid}/export')
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert archive.read('chapters/a.tex') == b'Chapter'
    with zipfile.ZipFile(io.BytesIO(client.get('/api/backup').content)) as archive:
        assert 'data/metadata.sqlite3' in archive.namelist()
        assert f'workspace/{pid}/main.tex' in archive.namelist()

def test_zip_slip_rejected_before_creation(client):
    response=client.post('/api/import',files={'file':('evil.zip',zip_data({'../evil':'bad'}))})
    assert response.status_code == 400
    assert client.get('/api/projects').json() == []

def test_move_main_and_delete(client):
    pid=create(client)
    assert client.post(f'/api/projects/{pid}/move',json={'source':'main.tex','destination':'doc.tex'}).status_code == 200
    assert client.put(f'/api/projects/{pid}',json={'name':'Novo','main':'doc.tex'}).status_code == 200
    assert client.delete(f'/api/projects/{pid}').status_code == 204
    assert client.get('/api/projects').json() == []

def test_origins_and_binary_upload(client):
    assert client.post('/api/projects',json={'name':'x'},headers={'Origin':'https://untrusted.example'}).status_code == 403
    pid=create(client)
    assert client.post(f'/api/projects/{pid}/upload?path=image.png',files={'file':('image.png',b'\x89PNG\r\n\x1a\n')}).status_code == 200
    assert client.get(f'/api/projects/{pid}/file?path=image.png').status_code == 415
