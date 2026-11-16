import './styles/main.css';
import {api,fileURL} from './services/api';
import {createEditor} from './editor/editor';
import {DraftsController,draftPath} from './drafts/controller';
import {ResearchPanel} from './components/research-panel';
import './styles/drafts.css';
import {PDFViewer} from './pdf/viewer';
const $=id=>document.getElementById(id);
import {shell} from './components/shell';
const html=shell;
$('app').innerHTML=html;
let projects=[],current=null,path=null,files=[],dirty=false,timer,autoTimer,pollTimer,saving=null,revision=0,shownVersion=null;
let research,drafts,fileHash=null;
let tabs=[]; let edits=0, requestedEdits=0;
const prefs=JSON.parse(localStorage.getItem('nexotex:prefs')||'{}');
document.documentElement.dataset.theme=prefs.theme||'dark';
$('auto').checked=!!prefs.auto;
function preference(key,value){prefs[key]=value;localStorage.setItem('nexotex:prefs',JSON.stringify(prefs));}
function message(text){$('message').textContent=text;}
async function safe(action){try{return await action();}catch(e){message(e.message);console.error(e);}}
const editor=createEditor($('editor'),content=>{
  if(!current||!path)return;
  dirty=true;revision++;if(!draftPath(path)){edits++;$('pdfState').textContent='Desatualizado';}drafts?.changed(); renderTabs();message('Alterações não salvas');
  localStorage.setItem(`draft:${current.id}:${path}`,content);
  clearTimeout(timer);timer=setTimeout(()=>safe(save),650);
},(line,col)=>$('cursor').textContent=`Ln ${line}, Col ${col}`);
editor.wrap(prefs.wrap!==false);
let font=prefs.font||14;document.documentElement.style.setProperty('--editor-size',`${font}px`);
const pdf=new PDFViewer($('pdf'),text=>$('pages').textContent=text);
async function loadProjects(selectId){projects=await api('/projects');$('projects').replaceChildren(new Option('Escolha um projeto',''),...projects.map(p=>new Option(p.name,p.id)));if(selectId&&projects.some(p=>p.id===selectId))await openProject(selectId);}
async function save(){
  clearTimeout(timer);
  if(saving){await saving;if(dirty)return save();return;}
  if(!dirty||!current||!path)return;
  const id=current.id,file=path,content=editor.content(),version=revision;
  saving=api(`/projects/${id}/file`,{method:'PUT',body:{path:file,content,expected_hash:fileHash}});
  try{const result=await saving;if(current?.id===id&&path===file)fileHash=result.hash;if(current?.id===id&&path===file&&revision===version){dirty=false;localStorage.removeItem(`draft:${id}:${file}`);message('Salvo no disco');renderTabs();}if($('auto').checked&&!draftPath(file)){clearTimeout(autoTimer);autoTimer=setTimeout(()=>safe(compile),1600);}}
  finally{saving=null;}
}
async function saveAll(){await save();await research?.save();}
async function openProject(id){
  await saveAll();await research?.reset();await drafts?.reset();fileHash=null;clearTimeout(autoTimer);clearTimeout(pollTimer);current=projects.find(p=>p.id===id)||null;path=null;tabs=[];edits=0;requestedEdits=0;shownVersion=null;dirty=false;editor.load('');renderTabs();
  $('tree').replaceChildren();$('projects').value=id;preference('project',id);$('welcome').hidden=!!current;$('editor').hidden=!current;
  pdf.doc?.destroy();pdf.doc=null;$('pdf').textContent='Compile para visualizar o documento.';$('pages').textContent='—';
  if(!current)return;
  await refreshTree();if(files.some(f=>f.path===current.main))await openFile(current.main);await poll(id);
}
async function refreshTree(){files=await api(`/projects/${current.id}/files`);renderTree();await drafts?.refresh();research?.choices();}
function renderTree(){
  const term=$('filter').value.toLowerCase();$('tree').replaceChildren();
  for(const file of files.filter(f=>!draftPath(f.path)&&f.path!=='rascunhos'&&!f.path.startsWith('rascunhos/')&&f.path.toLowerCase().includes(term))){
    const row=document.createElement('div');row.className='tree-row';
    const button=document.createElement('button');button.className='file'+(file.path===path?' active':'');button.textContent=`${file.directory?'▸':'·'} ${file.path}${file.path===current?.main?'  ★':''}`;button.title=file.path;button.onclick=()=>file.directory?null:safe(()=>file.path.toLowerCase().endsWith('.pdf')?research.openArticle(file.path):openFile(file.path));row.append(button);
    const menu=document.createElement('button');menu.textContent='···';menu.title='Mover ou excluir';menu.onclick=()=>safe(()=>manageFile(file.path));row.append(menu);$('tree').append(row);
  }
}
function renderTabs(){
  $('tabs').replaceChildren();for(const tab of tabs){const button=document.createElement('button');button.textContent=tab.split('/').pop()+(tab===path&&dirty?' •':'');button.className=tab===path?'selected':'';button.onclick=()=>safe(()=>openFile(tab));$('tabs').append(button);}
  $('fileLabel').textContent=path||'LATEX';
}
async function openFile(next){
  if(path===next)return;await saveAll();await research?.closePath(next);const response=await api(fileURL(current.id,next));path=next;fileHash=response.hash;revision++;dirty=false;
  const draft=localStorage.getItem(`draft:${current.id}:${path}`);const recover=draft!==null&&draft!==response.content&&confirm(`Recuperar alterações locais não salvas de ${path}?`);
  editor.load(recover?draft:response.content,`${current.id}:${path}`);if(!tabs.includes(path))tabs.push(path);renderTabs();renderTree();await drafts?.opened();editor.view.focus();
  if(recover){dirty=true;await save();}else localStorage.removeItem(`draft:${current.id}:${path}`);
}
async function newProject(){const name=prompt('Nome do projeto:','Meu TCC');if(!name?.trim())return;await save();const p=await api('/projects',{method:'POST',body:{name:name.trim()}});await loadProjects(p.id);}
async function newFile(directory=false){if(!current)throw Error('Crie ou abra um projeto');const name=prompt(directory?'Caminho da pasta:':'Caminho do arquivo:');if(!name)return;if(files.some(f=>f.path===name))throw Error('Este caminho já existe');await api(`/projects/${current.id}/file`,{method:'PUT',body:{path:name,content:'',directory}});await refreshTree();if(!directory)await openFile(name);}
async function manageFile(source,action=null){
  await saveAll();const destination=action==='excluir'?'':prompt('Novo caminho (deixe vazio para excluir):',source);if(destination===null||destination===source)return;await research?.closePath(source);
  if(!destination){if(!confirm(`Excluir ${source} e seu conteúdo?`))return;await api(fileURL(current.id,source),{method:'DELETE'});}else await api(`/projects/${current.id}/move`,{method:'POST',body:{source,destination}});
  tabs=tabs.filter(t=>t!==source&&!t.startsWith(source+'/'));if(path===source||path?.startsWith(source+'/')){path=null;editor.load('');}await refreshTree();renderTabs();await drafts?.opened();
}
async function compile(){if(!current)throw Error('Escolha um projeto');await saveAll();clearTimeout(autoTimer);requestedEdits=edits;await api(`/projects/${current.id}/compile`,{method:'POST'});await poll(current.id);}
async function poll(id){
  clearTimeout(pollTimer);const state=await api(`/projects/${id}/compile`);if(current?.id!==id)return;
  const busy=['running','queued'].includes(state.state);$('compile').textContent=busy?'◌ Compilando…':'▷ Compilar';
  $('logText').textContent=state.log||'Nenhuma compilação nesta sessão.';$('errors').replaceChildren();
  for(const error of state.errors||[]){const button=document.createElement('button');button.textContent=`${error.path}:${error.line} — ${error.message}`;button.onclick=()=>safe(async()=>{await openFile(error.path);editor.line(error.line);});$('errors').append(button);}
  if(state.state==='error'){$('pdfState').textContent='PDF anterior';message('Falha na compilação · último PDF pode estar desatualizado');$('logs').hidden=false;}
  if(state.pdf&&shownVersion!==state.version){await pdf.load(`/api/projects/${id}/pdf?v=${state.version}`,shownVersion===null);if(current?.id!==id)return;shownVersion=state.version;}
  if(state.state==='success'){$('pdfState').textContent=edits===requestedEdits?'Atualizado':'Desatualizado';message(edits===requestedEdits?'Compilação concluída':'PDF gerado · há alterações posteriores');}
  if(busy)pollTimer=setTimeout(()=>safe(()=>poll(id)),800);
}
$('newProject').onclick=$('welcomeCreate').onclick=()=>safe(newProject);
$('projects').onchange=()=>safe(()=>openProject($('projects').value));
$('newFile').onclick=()=>safe(()=>newFile());$('newFolder').onclick=()=>safe(()=>newFile(true));$('filter').oninput=renderTree;
$('compile').onclick=()=>safe(compile);
$('theme').onclick=()=>{document.documentElement.dataset.theme=document.documentElement.dataset.theme==='dark'?'light':'dark';preference('theme',document.documentElement.dataset.theme);};
$('auto').onchange=()=>{preference('auto',$('auto').checked);if(!$('auto').checked)clearTimeout(autoTimer);};
$('showLogs').onclick=()=>$('logs').hidden=!$('logs').hidden;$('closeLogs').onclick=()=>$('logs').hidden=true;
$('sidebarToggle').onclick=()=>document.body.classList.toggle('hide-sidebar');$('focus').onclick=()=>document.body.classList.toggle('focus');
$('wrap').onclick=()=>{preference('wrap',prefs.wrap===false);editor.wrap(prefs.wrap);};
function resizeFont(delta){font=Math.max(10,Math.min(26,font+delta));document.documentElement.style.setProperty('--editor-size',`${font}px`);preference('font',font);}
$('fontDown').onclick=()=>resizeFont(-1);$('fontUp').onclick=()=>resizeFont(1);
$('layout').value=prefs.layout||'split';function layout(){document.body.dataset.layout=$('layout').value;preference('layout',$('layout').value);} $('layout').onchange=layout;layout();
$('previous').onclick=()=>safe(()=>pdf.navigate(-1));$('next').onclick=()=>safe(()=>pdf.navigate(1));$('zoomIn').onclick=()=>safe(()=>pdf.scale(.1));$('zoomOut').onclick=()=>safe(()=>pdf.scale(-.1));
$('download').onclick=()=>{if(current&&pdf.doc)window.open(`/api/projects/${current.id}/pdf`,'_blank','noopener');};
$('export').onclick=async()=>safe(async()=>{await saveAll();if(current)window.location.href=`/api/projects/${current.id}/export`;});
$('backup').onclick=()=>safe(async()=>{await saveAll();window.location.href='/api/backup';});
$('import').onclick=()=>$('zipInput').click();$('zipInput').onchange=()=>safe(async()=>{const file=$('zipInput').files[0];if(!file)return;const form=new FormData();form.append('file',file);const p=await api('/import',{method:'POST',body:form});await loadProjects(p.id);$('zipInput').value='';});
$('upload').onclick=()=>{if(current)$('uploadInput').click();else message('Escolha um projeto');};$('uploadInput').onchange=()=>safe(async()=>{const file=$('uploadInput').files[0];if(!file)return;const target=prompt('Salvar no caminho:',file.name);if(!target)return;if(files.some(f=>f.path===target)&&!confirm('Substituir arquivo existente?'))return;const form=new FormData();form.append('file',file);await api(`/projects/${current.id}/upload?path=${encodeURIComponent(target)}`,{method:'POST',body:form});await refreshTree();$('uploadInput').value='';});
$('projectMenu').onclick=()=>{if(!current)return;$('projectName').value=current.name;$('mainFile').replaceChildren(...files.filter(f=>f.path.endsWith('.tex')).map(f=>new Option(f.path,f.path)));$('mainFile').value=current.main;$('settings').showModal();};
$('saveProject').onclick=()=>safe(async()=>{const updated=await api(`/projects/${current.id}`,{method:'PUT',body:{name:$('projectName').value,main:$('mainFile').value}});Object.assign(current,updated);$('projects').selectedOptions[0].textContent=current.name;renderTree();$('settings').close();});
$('deleteProject').onclick=()=>safe(async()=>{if(!confirm(`Excluir permanentemente ${current.name}? Exporte um ZIP para preservar uma cópia.`))return;await saveAll();await research.reset();await api(`/projects/${current.id}`,{method:'DELETE'});dirty=false;$('settings').close();await openProject('');await loadProjects();});
let drag=false;const panels=$('panels');panels.style.setProperty('--split',prefs.split||'50%');
$('divider').onpointerdown=e=>{drag=true;$('divider').setPointerCapture(e.pointerId);};$('divider').onpointermove=e=>{if(drag){const box=panels.getBoundingClientRect();const split=Math.max(25,Math.min(75,(e.clientX-box.left)/box.width*100))+'%';panels.style.setProperty('--split',split);preference('split',split);}};$('divider').onpointerup=()=>drag=false;
$('divider').onkeydown=e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();const n=parseFloat(prefs.split||50)+(e.key==='ArrowLeft'?-2:2);preference('split',Math.max(25,Math.min(75,n))+'%');panels.style.setProperty('--split',prefs.split);}};
document.addEventListener('keydown',e=>{if(!(e.ctrlKey||e.metaKey))return;if(e.shiftKey&&e.key.toLowerCase()==='f'){e.preventDefault();document.body.classList.toggle('focus');return;}if(e.key==='s'){e.preventDefault();safe(save);}if(e.key==='Enter'){e.preventDefault();safe(compile);}if(e.key==='p'){e.preventDefault();document.body.classList.remove('hide-sidebar','focus');$('filter').focus();}});
window.addEventListener('beforeunload',e=>{if(dirty||research?.dirty){e.preventDefault();e.returnValue='';}});
research=new ResearchPanel({project:()=>current,path:()=>path,files:()=>files,content:()=>draftPath(path)?editor.content():'',safe,message,reveal:()=>{if($('layout').value!=='split'){$('layout').value='split';layout();}},changed:file=>{if(!draftPath(file)&&$('auto').checked){clearTimeout(autoTimer);autoTimer=setTimeout(()=>safe(compile),1600);}},cite:key=>safe(async()=>{if(!drafts.active){message('Chave bibliográfica: '+key);return;}await drafts.references();$('referenceSearch').value=key;drafts.renderReferences();})});
drafts=new DraftsController({project:()=>current,path:()=>path,files:()=>files,editor,research,safe,message,saveAll,refreshFiles:refreshTree,open:openFile,manage:manageFile,reload:async()=>{const old=path;path=null;await openFile(old);}});
$('editor').hidden=true;safe(()=>loadProjects(prefs.project));
