import {api,fileURL} from '../services/api';
import {createEditor} from '../editor/editor';
import {PDFViewer} from '../pdf/viewer';
import {renderMarkdown} from '../drafts/markdown';
const $=id=>document.getElementById(id);
export class ResearchPanel {
  constructor(hooks) {
    this.h=hooks;this.path=null;this.hash=null;this.dirty=false;this.rev=0;this.pending=null;this.articlePath=null;
    const panel=document.querySelector('.pdf-panel');
    const bar=document.createElement('div');bar.className='research-bar';
    bar.innerHTML='<select id="rightMode" aria-label="Conteúdo do painel lateral"><option value="compiled">PDF compilado</option><option value="source">Arquivo ao lado</option><option value="article">Artigo PDF</option><option value="preview">Prévia Markdown</option></select><select id="rightFile" aria-label="Arquivo do painel"></select>';
    panel.prepend(bar);
    const source=document.createElement('div');source.id='sideEditor';source.hidden=true;panel.append(source);
    const article=document.createElement('div');article.id='articleArea';article.hidden=true;article.innerHTML='<div class="pdf-tools"><button id="articlePrevious">‹</button><input id="articlePage" type="number" min="1" value="1" aria-label="Página do artigo"><span id="articlePages"></span><button id="articleNext">›</button><button id="articleMinus">−</button><button id="articlePlus">+</button></div><div id="articleCanvas" class="article-canvas"></div>';panel.append(article);
    const preview=document.createElement('article');preview.id='markdownPreview';preview.className='markdown-body';preview.hidden=true;panel.append(preview);
    this.editor=createEditor(source,content=>{if(!this.path)return;this.dirty=true;this.rev++;localStorage.setItem(this.recoveryKey(),content);clearTimeout(this.timer);this.timer=setTimeout(()=>this.h.safe(()=>this.save()),650);this.h.message('Painel lateral · alterações não salvas');},()=>{});
    this.article=new PDFViewer($('articleCanvas'),text=>{$('articlePages').textContent=text;$('articlePage').value=this.article.page;if(this.articlePath)localStorage.setItem(`article:${this.h.project()?.id}:${this.articlePath}`,String(this.article.page));});
    $('rightMode').onchange=()=>this.h.safe(()=>this.setMode($('rightMode').value));
    $('rightFile').onchange=()=>this.h.safe(()=>$('rightMode').value==='article'?this.openArticle($('rightFile').value):this.openSource($('rightFile').value));
    $('articlePrevious').onclick=()=>this.h.safe(()=>this.article.navigate(-1));$('articleNext').onclick=()=>this.h.safe(()=>this.article.navigate(1));
    $('articleMinus').onclick=()=>this.h.safe(()=>this.article.scale(-.1));$('articlePlus').onclick=()=>this.h.safe(()=>this.article.scale(.1));
    $('articlePage').onchange=()=>this.h.safe(async()=>{if(!this.article.doc)return;const p=Number($('articlePage').value);this.article.page=Math.max(1,Math.min(this.article.doc.numPages,p));await this.article.render();});
    preview.addEventListener('click',event=>{const a=event.target.closest('a');if(!a)return;const url=new URL(a.href);if(url.pathname==='/nexotex/pdf'){event.preventDefault();this.h.safe(()=>this.openArticle(url.searchParams.get('path'),Number(url.searchParams.get('page')||1)));}else if(url.pathname==='/nexotex/tex'){event.preventDefault();this.h.safe(()=>this.openSource(url.searchParams.get('path')));}else if(url.pathname==='/nexotex/cite'){event.preventDefault();this.h.cite?.(url.searchParams.get('key'));}});
  }
  recoveryKey(){return `draft:${this.h.project()?.id}:${this.path}`;}
  async reset(){clearTimeout(this.timer);await this.save();this.path=null;this.dirty=false;this.editor.load('');this.articlePath=null;await this.article.doc?.destroy();this.article.doc=null;$('articleCanvas').replaceChildren();this.mode='compiled';await this.setMode('compiled',false);}
  async save(){
    clearTimeout(this.timer);if(this.pending){await this.pending;if(this.dirty)return this.save();return;}
    if(!this.dirty||!this.path)return;
    const id=this.h.project().id,path=this.path,content=this.editor.content(),revision=this.rev;
    this.pending=api(`/projects/${id}/file`,{method:'PUT',body:{path,content,expected_hash:this.hash}});
    try{const result=await this.pending;this.hash=result.hash;if(revision===this.rev){this.dirty=false;localStorage.removeItem(this.recoveryKey());this.h.message('Painel lateral · salvo no disco');}this.h.changed?.(path);}
    finally{this.pending=null;}
  }
  files(){return this.h.files().filter(f=>!f.directory);}
  choices(){const mode=this.mode,paths=this.files().filter(f=>mode==='article'?f.path.toLowerCase().endsWith('.pdf'):/\.(tex|md|bib)$/.test(f.path));$('rightFile').replaceChildren(new Option(mode==='article'?'Escolha um PDF':'Escolha um arquivo',''),...paths.map(f=>new Option(f.path,f.path)));$('rightFile').value=mode==='article'?(this.articlePath||''):(this.path||'');$('rightFile').hidden=!['article','source'].includes(mode);}
  async setMode(mode,reveal=true){
    this.mode=mode;$('rightMode').value=mode;this.choices();
    document.querySelector('.pdf-panel > .pdf-tools').hidden=mode!=='compiled';$('pdf').hidden=mode!=='compiled';$('sideEditor').hidden=mode!=='source';$('articleArea').hidden=mode!=='article';$('markdownPreview').hidden=mode!=='preview';
    if(mode==='preview')this.preview(this.h.content());
    if(reveal)this.h.reveal();
  }
  preview(content){if(this.mode==='preview')renderMarkdown($('markdownPreview'),content);}
  async openSource(path){
    if(!path)return;if(path===this.h.path()){this.h.message('Este arquivo já está no editor principal. Escolha outro arquivo para o painel.');return;}
    await this.save();const id=this.h.project().id,response=await api(fileURL(id,path));this.path=path;this.hash=response.hash;this.rev++;this.dirty=false;
    const recovered=localStorage.getItem(this.recoveryKey());const recover=recovered!==null&&recovered!==response.content&&confirm(`Recuperar alterações locais de ${path}?`);
    this.editor.load(recover?recovered:response.content,`${id}:${path}`);await this.setMode('source');
    if(recover){this.dirty=true;await this.save();}else localStorage.removeItem(this.recoveryKey());
  }
  async reload(path){if(path===this.path){await this.save();const response=await api(fileURL(this.h.project().id,path));this.hash=response.hash;this.editor.load(response.content,`${this.h.project().id}:${path}`);}}
  async openArticle(path,page=null){
    if(!path)return;const id=this.h.project().id;
    await this.setMode('article');if(this.articlePath!==path){await this.article.load(`/api/projects/${id}/article?path=${encodeURIComponent(path)}`,true);this.articlePath=path;const saved=Number(localStorage.getItem(`article:${id}:${path}`)||1);this.article.page=Math.max(1,Math.min(page||saved,this.article.doc.numPages));await this.article.render();}
    else if(page){this.article.page=Math.max(1,Math.min(page,this.article.doc.numPages));await this.article.render();}this.choices();
  }
  selectedArticle(){const selection=window.getSelection();return {pdf_path:this.mode==='article'?this.articlePath:null,page:this.article.page,quote:selection?.anchorNode&&$('articleCanvas').contains(selection.anchorNode)&&$('articleCanvas').contains(selection.focusNode)?selection.toString():''};}
  async closePath(source){if(this.path&&(this.path===source||this.path.startsWith(source+'/'))){await this.save();this.path=null;this.dirty=false;this.editor.load('');await this.setMode('compiled');}}
}
