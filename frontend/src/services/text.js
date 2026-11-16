// CodeMirror/DOM offsets use UTF-16; backend slicing uses Unicode code points.
export const codePointOffset = (text, utf16Offset) => Array.from(text.slice(0,utf16Offset)).length;
export function countText(text) {
  const words=text.match(/[\p{L}\p{N}]+(?:[’'-][\p{L}\p{N}]+)*/gu)||[];
  return {words:words.length,characters:Array.from(text).length};
}
export function insertionPosition(content,mode,line=1,cursor=null) {
  if(mode==='cursor') {if(cursor===null)throw Error('Abra o arquivo de destino no painel ao lado para usar o cursor.');return codePointOffset(content,cursor);}
  if(mode==='start')return 0;
  if(mode==='end')return Array.from(content).length;
  if(mode==='before-end'){const index=content.lastIndexOf('\\end{document}');return index<0?Array.from(content).length:codePointOffset(content,index);}
  const lines=content.split('\n');if(!Number.isInteger(line)||line<1||line>lines.length)throw Error('Linha de inserção inválida.');
  return Array.from(lines.slice(0,line-1).map(x=>x+'\n').join('')).length;
}
