import {api,fileURL} from '../services/api';
import {codePointOffset,countText,insertionPosition} from '../services/text';
const $=id=>document.getElementById(id);
const states={idea:'Ideia',writing:'Em desenvolvimento',review:'Em revisão',integrated:'Integrado ao LaTeX'};
const kinds={idea:['Ideia','#d6b85e'],reference:['Precisa de referência','#84bca4'],question:['Dúvida','#d88a8a'],review:['Revisar','#ae99d6'],task:['Tarefa','#85b2cf']};
const draftPath=path=>path?.toLowerCase().endsWith('.md');
export class DraftsController {
  constructor(hooks) {
    this.h=hooks;this.items=[];this.refs=[];this.meta=null;this.searchSequence=0;this.versionContent=null;
    const nav=document.createElement('section');nav.className='draft-explorer';nav.innerHTML='<div class="section-title">RASCUNHOS <button id="newDraft" title="Criar rascunho">+</button></div><input id="draftSearch" placeholder="Buscar nome ou conteúdo…" aria-label="Buscar rascunhos"><nav id="draftTree"></nav>';
    $('tree').after(nav);
    const bar=document.createElement('div');bar.id='draftBar';bar.hidden=true;bar.innerHTML='<div class="draft-title-row"><input id="draftTitle" aria-label="Título do rascunho"><select id="draftState" aria-label="Estado do rascunho"></select><span id="draftCounts"></span></div><div class="draft-format"><button id="draftBold" title="Negrito · Ctrl+B"><b>B</b></button><button id="draftItalic" title="Itálico · Ctrl+I"><i>I</i></button><button id="draftHeading" title="Título">H</button><button id="draftList" title="Lista">• Lista</button><button id="draftCheck" title="Checklist">☐</button><button id="draftQuote" title="Citação em bloco">❯</button><button id="draftMath" title="Fórmula">∑</button><button id="draftCite">Referências</button><button id="draftPreview">Prévia</button><button id="draftDetails">Detalhes</button><button id="draftHistory">Versões</button><div class="spacer"></div><button id="draftTransfer" class="primary">Enviar para LaTeX</button></div>';
    $('editor').before(bar);
    const details=document.createElement('section');details.id='draftInspector';details.hidden=true;details.innerHTML='<div class="draft-links"><label>Arquivo LaTeX<select id="draftLinked"></select></label><label>Seção<input id="draftSection" placeholder="Ex.: Introdução"></label><button id="openLinked">Abrir ao lado</button><button id="jumpLinked">Alternar para LaTeX</button></div><p id="draftDates" class="muted"></p><div class="section-title">OBSERVAÇÕES <button id="newObservation">+ Observação</button></div><div id="observations"></div>';
    $('editor').before(details);
    const dialogs=document.createElement('div');dialogs.innerHTML=`
    <dialog id="draftTransferDialog" class="wide-dialog"><h2>Enviar para LaTeX</h2><p class="muted">O destino receberá uma inserção. O rascunho original permanece disponível.</p><div class="form-grid"><label>Destino<select id="transferTarget"></select></label><label>Conteúdo<select id="transferRange"><option value="all">Rascunho inteiro</option><option value="selection">Trecho selecionado</option></select></label><label>Inserir<select id="transferPosition"><option value="before-end">Antes de \\end{document}, ou no fim</option><option value="cursor">No cursor do painel LaTeX</option><option value="start">No início</option><option value="end">No fim</option><option value="line">Antes da linha indicada</option></select></label><label>Linha<input id="transferLine" type="number" min="1" value="1"></label><label>Citações<select id="transferStyle"><option value="auto">Detectar pelo projeto</option><option value="latex">LaTeX · cite</option><option value="abntex2">abnTeX2</option><option value="natbib">natbib</option><option value="biblatex">biblatex</option></select></label></div><button id="generateTransfer">Gerar prévia</button><p id="transferMessage" role="status"></p><textarea id="transferFragment" readonly aria-label="LaTeX convertido" placeholder="O resultado convertido aparecerá aqui."></textarea><details><summary>Contexto da inserção</summary><pre id="transferContext"></pre></details><div class="dialog-actions"><button id="cancelTransfer">Cancelar</button><button id="applyTransfer" class="primary" disabled>Confirmar inserção</button></div></dialog>
    <dialog id="draftObservationDialog"><h2>Observação</h2><div class="form-grid"><label>Categoria<select id="observationKind"></select></label><label>Cor<input id="observationColor" type="color"></label></div><label>Observação<textarea id="observationText" rows="4" maxlength="10000"></textarea></label><label>Trecho no rascunho<textarea id="observationSource" rows="2" maxlength="10000"></textarea></label><label>Artigo<select id="observationPDF"></select></label><label>Página<input id="observationPage" type="number" min="1"></label><label>Trecho do artigo<textarea id="observationQuote" rows="3" maxlength="10000"></textarea></label><label>Referência<select id="observationRef"></select></label><div class="dialog-actions"><button id="cancelObservation">Cancelar</button><button id="saveObservation" class="primary">Salvar observação</button></div></dialog>
    <dialog id="draftHistoryDialog" class="wide-dialog"><h2>Versões do rascunho</h2><p class="muted">Até 50 versões. Registros automáticos a cada cinco minutos de alterações, antes de restaurar e ao integrar.</p><button id="snapshotDraft">Guardar versão agora</button><select id="draftVersions" aria-label="Versões disponíveis"></select><textarea id="draftVersionContent" readonly aria-label="Conteúdo da versão" rows="12"></textarea><div class="dialog-actions"><button id="closeHistory">Fechar</button><button id="restoreDraft" class="primary" disabled>Restaurar esta versão</button></div></dialog>
    <dialog id="draftReferencesDialog"><h2>Referências do projeto</h2><input id="referenceSearch" placeholder="Buscar autor, título ou chave" aria-label="Buscar referência"><div id="referenceList"></div><div class="dialog-actions"><button id="closeReferences">Fechar</button></div></dialog>`;
    document.body.append(dialogs);
    $('draftState').replaceChildren(...Object.entries(states).map(([value,label])=>new Option(label,value)));
    $('observationKind').replaceChildren(...Object.entries(kinds).map(([value,[label]])=>new Option(label,value)));
    const bind=(id,fn)=>$(id).onclick=()=>this.h.safe(fn);
    bind('newDraft',()=>this.create());$('draftSearch').oninput=()=>{clearTimeout(this.searchTimer);this.searchTimer=setTimeout(()=>this.h.safe(()=>this.refresh()),200);};
    bind('draftBold',()=>this.h.editor.format('**'));bind('draftItalic',()=>this.h.editor.format('*'));
    for(const [id,text] of [['draftHeading','## Título\n'],['draftList','\n- Item\n'],['draftCheck','\n- [ ] Tarefa\n'],['draftQuote','\n> Observação\n'],['draftMath','$E = mc^2$']])bind(id,()=>this.h.editor.insert(text));
    bind('draftPreview',()=>this.h.research.setMode('preview'));
    bind('draftDetails',()=>{$('draftInspector').hidden=!$('draftInspector').hidden;});
    for(const id of ['draftTitle','draftState','draftLinked','draftSection'])$(id).onchange=()=>this.h.safe(()=>this.saveMeta());
    bind('openLinked',()=>{if(this.meta?.linked_tex)return this.h.research.openSource(this.meta.linked_tex);throw Error('Escolha primeiro o arquivo LaTeX associado.');});
    bind('jumpLinked',()=>{if(this.meta?.linked_tex)return this.h.open(this.meta.linked_tex);});
    bind('newObservation',()=>this.observation());$('observationKind').onchange=()=>$('observationColor').value=kinds[$('observationKind').value][1];
    bind('saveObservation',()=>this.saveObservation());$('cancelObservation').onclick=()=>$('draftObservationDialog').close();
    bind('draftTransfer',()=>this.transfer());bind('generateTransfer',()=>this.generate());bind('applyTransfer',()=>this.apply());$('cancelTransfer').onclick=()=>$('draftTransferDialog').close();
    for(const id of ['transferTarget','transferRange','transferPosition','transferLine','transferStyle'])$(id).onchange=()=>{this.preview=null;$('applyTransfer').disabled=true;$('transferFragment').value='';};
    bind('draftHistory',()=>this.history());bind('snapshotDraft',()=>this.snapshot());bind('restoreDraft',()=>this.restore());$('closeHistory').onclick=()=>$('draftHistoryDialog').close();$('draftVersions').onchange=()=>this.h.safe(()=>this.showVersion());
    bind('draftCite',()=>this.references());$('referenceSearch').oninput=()=>this.renderReferences();$('closeReferences').onclick=()=>$('draftReferencesDialog').close();
  }
  base(){return `/projects/${this.h.project().id}`;}
  get active(){return draftPath(this.h.path());}
  async reset(){this.items=[];this.meta=null;++this.searchSequence;$('draftTree').replaceChildren();$('draftBar').hidden=true;$('draftInspector').hidden=true;$('draftSearch').value='';}
  async refresh(){
    if(!this.h.project())return;const sequence=++this.searchSequence,id=this.h.project().id;
    const rows=await api(`/projects/${id}/drafts?q=${encodeURIComponent($('draftSearch').value)}`);
    if(sequence!==this.searchSequence||id!==this.h.project()?.id)return;
    this.items=rows;this.render();
  }
  render(){
    $('draftTree').replaceChildren();
    for(const item of this.items){const row=document.createElement('div');row.className='tree-row';const button=document.createElement('button');button.className='file'+(item.path===this.h.path()?' active':'');button.textContent=item.path.replace(/^rascunhos\//,'')+' · '+states[item.state];button.title=item.title;button.onclick=()=>this.h.safe(()=>this.h.open(item.path));row.append(button);const menu=document.createElement('button');menu.textContent='···';menu.title='Renomear, duplicar ou excluir rascunho';menu.onclick=()=>this.h.safe(()=>this.manage(item.path));row.append(menu);$('draftTree').append(row);}
    if(!this.items.length){const p=document.createElement('p');p.className='muted';p.textContent='Crie um rascunho ou refine a busca.';$('draftTree').append(p);}
  }
  async create(){if(!this.h.project())throw Error('Abra um projeto primeiro.');let path=prompt('Caminho do rascunho:','rascunhos/ideias.md');if(!path)return;if(!path.endsWith('.md'))path+='.md';await this.h.saveAll();await api(this.base()+'/drafts',{method:'POST',body:{path,content:'# '+path.split('/').pop().replace(/\.md$/,'')+'\n\n'}});await this.h.refreshFiles();await this.refresh();await this.h.open(path);}
  async manage(path){
    const action=prompt('Ação: renomear, duplicar ou excluir','renomear');if(!action)return;
    if(action==='renomear'||action==='excluir'){await this.h.manage(path,action);await this.refresh();return;}
    if(action!=='duplicar')throw Error('Use renomear, duplicar ou excluir.');
    const destination=prompt('Caminho da cópia:',path.replace(/\.md$/,'-copia.md'));if(!destination)return;
    await this.h.saveAll();const response=await api(fileURL(this.h.project().id,path));await api(this.base()+'/drafts',{method:'POST',body:{path:destination,content:response.content}});
    const meta=await api(this.base()+`/drafts/meta?path=${encodeURIComponent(path)}`);
    await api(this.base()+`/drafts/meta?path=${encodeURIComponent(destination)}`,{method:'PUT',body:{...this.metaValues(meta),title:meta.title+' (cópia)',state:'idea'}});
    await this.h.refreshFiles();await this.refresh();await this.h.open(destination);
  }
  metaValues(meta=this.meta){return Object.fromEntries(['title','state','linked_tex','section','references','observations'].map(k=>[k,meta[k]]));}
  async opened(){
    const path=this.h.path();document.querySelector('.editor-panel').dataset.document=this.active?'markdown':'latex';$('draftBar').hidden=!this.active;$('draftInspector').hidden=true;this.render();
    if(!this.active){this.meta=null;return;}
    const meta=await api(this.base()+`/drafts/meta?path=${encodeURIComponent(path)}`);if(path!==this.h.path())return;this.meta=meta;
    $('draftTitle').value=meta.title;$('draftState').value=meta.state;$('draftSection').value=meta.section;
    $('draftLinked').replaceChildren(new Option('Sem associação',''),...this.h.files().filter(f=>f.path.endsWith('.tex')).map(f=>new Option(f.path,f.path)));$('draftLinked').value=meta.linked_tex||'';
    $('draftDates').textContent=`Criado em ${new Date(meta.created_at*1000).toLocaleString('pt-BR')} · Modificado em ${new Date(meta.modified_at*1000).toLocaleString('pt-BR')}`;
    this.changed();this.renderObservations();
  }
  changed(){if(!this.active)return;const count=countText(this.h.editor.content());$('draftCounts').textContent=`${count.words} palavras · ${count.characters} caracteres`;this.h.research.preview(this.h.editor.content());}
  async saveMeta(values=null){if(!this.meta)return;const path=this.h.path();const body=values||{...this.metaValues(),title:$('draftTitle').value,state:$('draftState').value,linked_tex:$('draftLinked').value||null,section:$('draftSection').value};
    const updated=await api(this.base()+`/drafts/meta?path=${encodeURIComponent(path)}`,{method:'PUT',body});if(path===this.h.path())this.meta=updated;await this.refresh();this.h.message('Metadados do rascunho salvos');}
  async observation(existing=null){
    if(!this.active)return;this.editObservation=existing?.id||null;
    const selected=this.h.editor.view.state.selection.main,source=this.h.editor.view.state.sliceDoc(selected.from,selected.to),article=this.h.research.selectedArticle();
    $('observationKind').value=existing?.kind||'idea';$('observationColor').value=existing?.color||kinds.idea[1];$('observationText').value=existing?.text||'';$('observationSource').value=existing?.source_quote||source;
    const pdfs=this.h.files().filter(f=>f.path.toLowerCase().endsWith('.pdf'));$('observationPDF').replaceChildren(new Option('Sem artigo',''),...pdfs.map(f=>new Option(f.path,f.path)));$('observationPDF').value=existing?.pdf_path||article.pdf_path||'';
    $('observationPage').value=existing?.page||(article.pdf_path?article.page:'');$('observationQuote').value=existing?.quote||article.quote||'';
    this.refs=await api(this.base()+'/references');$('observationRef').replaceChildren(new Option('Sem referência',''),...this.refs.map(r=>new Option(r.key,r.key)));$('observationRef').value=existing?.ref_key||'';
    $('draftObservationDialog').showModal();$('observationText').focus();
  }
  async saveObservation(){
    if(!$('observationText').value.trim())throw Error('Escreva uma observação.');
    const note={id:this.editObservation||crypto.randomUUID(),kind:$('observationKind').value,color:$('observationColor').value,text:$('observationText').value,source_quote:$('observationSource').value,quote:$('observationQuote').value,pdf_path:$('observationPDF').value||null,page:$('observationPage').value?Number($('observationPage').value):null,ref_key:$('observationRef').value};
    const observations=this.meta.observations.filter(n=>n.id!==note.id);observations.push(note);
    const references=[...new Set([...this.meta.references,...(note.ref_key?[note.ref_key]:[])])];await this.saveMeta({...this.metaValues(),observations,references});$('draftObservationDialog').close();$('draftInspector').hidden=false;this.renderObservations();
  }
  renderObservations(){
    $('observations').replaceChildren();for(const note of this.meta?.observations||[]){const card=document.createElement('article');card.className='observation';card.style.setProperty('--note-color',note.color);
      const title=document.createElement('strong');title.textContent=kinds[note.kind][0];const text=document.createElement('p');text.textContent=note.text;card.append(title,text);
      for(const [label,value] of [['Rascunho',note.source_quote],['Artigo',note.quote]])if(value){const quote=document.createElement('blockquote');quote.textContent=label+': '+value;card.append(quote);}
      const action=(label,handler)=>{const b=document.createElement('button');b.textContent=label;b.onclick=()=>this.h.safe(handler);card.append(b);};
      if(note.pdf_path)action(`${note.pdf_path.split('/').pop()} · p. ${note.page||1}`,()=>this.h.research.openArticle(note.pdf_path,note.page||1));
      if(note.source_quote)action('Localizar trecho',()=>{const at=this.h.editor.content().indexOf(note.source_quote);if(at<0)throw Error('O trecho mudou; edite a observação para atualizar o vínculo.');if(this.h.editor.content().indexOf(note.source_quote,at+1)>=0)throw Error('O trecho aparece mais de uma vez. Edite a observação com um contexto mais específico.');this.h.editor.view.dispatch({selection:{anchor:at,head:at+note.source_quote.length},scrollIntoView:true});this.h.editor.view.focus();});
      action('Inserir bloco no rascunho',()=>{const link=note.pdf_path?`\n> [Artigo, p. ${note.page||1}](/nexotex/pdf?path=${encodeURIComponent(note.pdf_path)}&page=${note.page||1})`:'';this.h.editor.insert(`\n> **${kinds[note.kind][0]}:** ${note.text.replace(/\n/g,'\n> ')}${link}\n`);});
      action('Editar',()=>this.observation(note));action('Excluir',async()=>{if(!confirm('Excluir esta observação?'))return;await this.saveMeta({...this.metaValues(),observations:this.meta.observations.filter(n=>n.id!==note.id)});this.renderObservations();});$('observations').append(card);
    }
  }
  async transfer(){
    await this.h.saveAll();this.transferPath=this.h.path();this.transferSelection={...this.h.editor.view.state.selection.main};
    $('transferTarget').replaceChildren(...this.h.files().filter(f=>f.path.endsWith('.tex')).map(f=>new Option(f.path,f.path)));
    $('transferTarget').value=this.meta?.linked_tex||this.h.research.path||this.h.project().main;
    $('transferRange').value=this.transferSelection.from!==this.transferSelection.to?'selection':'all';this.preview=null;$('applyTransfer').disabled=true;$('transferFragment').value='';$('transferContext').textContent='';$('transferMessage').textContent='Escolha o destino e gere uma prévia antes de confirmar.';$('draftTransferDialog').showModal();
  }
  async generate(){
    this.preview=null;$('applyTransfer').disabled=true;await this.h.saveAll();if(this.h.path()!==this.transferPath)throw Error('O arquivo ativo mudou; reabra o envio.');
    const target=$('transferTarget').value;if(!target)throw Error('O projeto precisa de um arquivo .tex de destino.');
    const original=await api(fileURL(this.h.project().id,target));const cursor=this.h.research.path===target?this.h.research.editor.view.state.selection.main.from:null;
    const position=insertionPosition(original.content,$('transferPosition').value,Number($('transferLine').value),cursor);
    const source=this.h.editor.content(),range=$('transferRange').value==='selection'?{start:codePointOffset(source,this.transferSelection.from),end:codePointOffset(source,this.transferSelection.to)}:{};
    const preview=await api(this.base()+'/drafts/preview',{method:'POST',body:{path:this.transferPath,destination:target,position,...range,citation_style:$('transferStyle').value}});
    this.preview=preview;$('transferFragment').value=preview.fragment;$('transferContext').textContent=preview.before+'\n[CONTEÚDO CONVERTIDO SERÁ INSERIDO AQUI]\n'+preview.after;$('transferMessage').textContent=preview.warnings.join(' ')||'Confira o trecho. O arquivo de destino só mudará após confirmar.';$('applyTransfer').disabled=false;
  }
  async apply(){
    if(!this.preview)return;await this.h.saveAll();$('applyTransfer').disabled=true;
    try{const result=await api(this.base()+'/drafts/apply',{method:'POST',body:{token:this.preview.token,confirmed:true}});await this.h.research.reload(result.path);$('draftTransferDialog').close();this.preview=null;await this.h.refreshFiles();this.h.message('Trecho inserido no LaTeX. O rascunho foi preservado.');await this.h.research.openSource(result.path);}
    catch(error){$('transferMessage').textContent=error.message;this.preview=null;throw error;}
  }
  async history(){await this.h.saveAll();$('draftHistoryDialog').showModal();await this.loadVersions();}
  async loadVersions(){const versions=await api(this.base()+`/drafts/history?path=${encodeURIComponent(this.h.path())}`);$('draftVersions').replaceChildren(new Option('Escolha uma versão',''),...versions.map(v=>new Option(new Date(v.created_at*1000).toLocaleString('pt-BR')+' · '+v.reason,v.id)));$('draftVersionContent').value='';$('restoreDraft').disabled=true;}
  async showVersion(){const id=$('draftVersions').value;if(!id)return;const v=await api(this.base()+`/drafts/version?path=${encodeURIComponent(this.h.path())}&version_id=${id}`);$('draftVersionContent').value=v.content;$('restoreDraft').disabled=false;}
  async snapshot(){await this.h.saveAll();await api(this.base()+`/drafts/history?path=${encodeURIComponent(this.h.path())}`,{method:'POST'});await this.loadVersions();}
  async restore(){if(!confirm('Restaurar esta versão? O conteúdo atual será guardado no histórico antes.'))return;await this.h.saveAll();const path=this.h.path(),file=await api(fileURL(this.h.project().id,path));await api(this.base()+'/drafts/restore',{method:'POST',body:{path,version_id:$('draftVersions').value,expected_hash:file.hash}});$('draftHistoryDialog').close();await this.h.reload();this.h.message('Versão restaurada; conteúdo anterior preservado no histórico.');}
  async references(){this.refs=await api(this.base()+'/references');$('referenceSearch').value='';this.renderReferences();$('draftReferencesDialog').showModal();}
  renderReferences(){
    const term=$('referenceSearch').value.toLocaleLowerCase();$('referenceList').replaceChildren();for(const ref of this.refs.filter(r=>(r.key+' '+r.title+' '+r.authors).toLocaleLowerCase().includes(term))){const row=document.createElement('div');row.className='reference-row';const label=document.createElement('p');label.textContent=ref.key+' · '+ref.title+' · '+ref.authors;row.append(label);const button=document.createElement('button');button.textContent='Inserir citação';button.onclick=()=>this.h.safe(async()=>{this.h.editor.insert(`[@${ref.key}]`);if(!this.meta.references.includes(ref.key))await this.saveMeta({...this.metaValues(),references:[...this.meta.references,ref.key]});$('draftReferencesDialog').close();});row.append(button);const link=document.createElement('button');link.textContent='Inserir link interno';link.onclick=()=>this.h.safe(async()=>{this.h.editor.insert(`[${ref.key}](/nexotex/cite?key=${encodeURIComponent(ref.key)})`);if(!this.meta.references.includes(ref.key))await this.saveMeta({...this.metaValues(),references:[...this.meta.references,ref.key]});$('draftReferencesDialog').close();});row.append(link);$('referenceList').append(row);}
    if(!$('referenceList').children.length)$('referenceList').textContent='Nenhuma entrada encontrada nos arquivos .bib do projeto.';
  }
}
export {draftPath};
