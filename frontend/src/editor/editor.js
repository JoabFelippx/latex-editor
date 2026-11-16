import {EditorView, keymap} from '@codemirror/view';
import {EditorState, Compartment} from '@codemirror/state';
import {markdown} from '@codemirror/lang-markdown';
import {basicSetup} from 'codemirror';
import {tags} from '@lezer/highlight';
import {HighlightStyle,syntaxHighlighting,StreamLanguage} from '@codemirror/language';
import {stex} from '@codemirror/legacy-modes/mode/stex';
import {autocompletion, snippetCompletion} from '@codemirror/autocomplete';
const options = [
  ['section', '\\section{${Título}}'], ['subsection', '\\subsection{${Título}}'],
  ...['figure','table','equation','align'].map(env => [env, `\\begin{${env}}\n\t\${conteúdo}\n\\end{${env}}`]),
  ...['cite','ref','label','input','include'].map(cmd => [cmd, `\\${cmd}{\${chave}}`]),
].map(([label, template]) => snippetCompletion(template, {label:`\\${label}`,type:'keyword'}));
export function createEditor(parent, onChange, onCursor) {
  let suppress = false; let activeKey=null; const states=new Map();
  const wrapping = new Compartment();
  let markdownMode=false;
  const extensions = (isMarkdown=false) => [
    basicSetup,syntaxHighlighting(HighlightStyle.define([{tag:tags.keyword,color:'var(--syntax-keyword)'},{tag:tags.string,color:'var(--syntax-string)'},{tag:tags.comment,color:'var(--muted)'},{tag:tags.heading,color:'var(--accent)',fontWeight:'bold'},{tag:tags.number,color:'var(--syntax-number)'},{tag:tags.emphasis,fontStyle:'italic'},{tag:tags.strong,fontWeight:'bold'}])), isMarkdown ? markdown() : StreamLanguage.define(stex), wrapping.of(EditorView.lineWrapping),
    autocompletion({override: [context => {
      const word = context.matchBefore(/\\\w*/);
      return word ? {from:word.from, options} : null;
    }]}),
    keymap.of([{key:'Mod-s',run:()=>true},{key:'Mod-b',run:()=>markdownMode?format('**'):false},{key:'Mod-i',run:()=>markdownMode?format('*'):false}]),
    EditorView.updateListener.of(update => {
      if (update.docChanged && !suppress) onChange(view.state.doc.toString());
      if (update.selectionSet || update.docChanged) {
        const head = view.state.selection.main.head, line = view.state.doc.lineAt(head);
        onCursor(line.number, head - line.from + 1);
      }
    }),
    EditorView.theme({'&':{height:'100%',fontSize:'var(--editor-size, 14px)'},'.cm-scroller':{fontFamily:'"SFMono-Regular", Consolas, "Liberation Mono", monospace'},'.cm-content':{padding:'18px 0'},'.cm-gutters':{backgroundColor:'var(--surface)',color:'var(--muted)',border:'none'},'&.cm-focused':{outline:'none'}}),
  ];
  const view = new EditorView({parent,state:EditorState.create({extensions:extensions()})});
  function format(mark) {
    const selection=view.state.selection.main;
    const selected=view.state.sliceDoc(selection.from,selection.to)||'texto';
    view.dispatch({changes:{from:selection.from,to:selection.to,insert:mark+selected+mark},selection:{anchor:selection.from+mark.length,head:selection.from+mark.length+selected.length},userEvent:'input'});
    view.focus();return true;
  }
  return {view,format,
    insert(text) {const sel=view.state.selection.main;view.dispatch({changes:{from:sel.from,to:sel.to,insert:text},selection:{anchor:sel.from+text.length},userEvent:'input'});view.focus();},
    load(content,key=null) {suppress=true;if(activeKey)states.set(activeKey,view.state);activeKey=key;markdownMode=!!key?.endsWith('.md');const cached=states.get(key);view.setState(cached&&cached.doc.toString()===content?cached:EditorState.create({doc:content,extensions:extensions(markdownMode)}));suppress=false;},
    wrap(enabled) {view.dispatch({effects:wrapping.reconfigure(enabled ? EditorView.lineWrapping : [])});},
    line(number) {const line=view.state.doc.line(Math.max(1, Math.min(number,view.state.doc.lines))); view.dispatch({selection:{anchor:line.from},scrollIntoView:true}); view.focus();},
    content:()=>view.state.doc.toString()};
}
