import MarkdownIt from 'markdown-it';
import texmath from 'markdown-it-texmath';
import katex from 'katex';
import DOMPurify from 'dompurify';
import 'katex/dist/katex.min.css';
import {countText} from '../services/text';
const md=new MarkdownIt({html:false,linkify:false,typographer:false}).use(texmath,{engine:katex,delimiters:['dollars','brackets','beg_end'],katexOptions:{trust:false,throwOnError:false,strict:'ignore',maxExpand:1000}});
export function renderMarkdown(container,content) {
  container.innerHTML=DOMPurify.sanitize(md.render(content),{USE_PROFILES:{html:true,mathMl:true,svg:true},FORBID_TAGS:['style','iframe','object','embed','form'],FORBID_ATTR:['onerror','onload']});
  // Task-list syntax remains standard Markdown in the source file.
  for(const paragraph of container.querySelectorAll('li > p, li')) {
    const first=paragraph.firstChild;
    if(first?.nodeType===Node.TEXT_NODE&&/^\[[ xX]\] /.test(first.textContent)) {
      const box=document.createElement('input');box.type='checkbox';box.disabled=true;box.checked=/^\[[xX]\]/.test(first.textContent);first.textContent=first.textContent.slice(4);paragraph.prepend(box);
    }
  }
  for(const link of container.querySelectorAll('a')){if(!link.getAttribute('href')?.startsWith('/nexotex/')){link.target='_blank';link.rel='noopener noreferrer';}}
}
export {countText};
