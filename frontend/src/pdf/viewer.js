import 'pdfjs-dist/web/pdf_viewer.css';
import {getDocument, GlobalWorkerOptions, TextLayer} from 'pdfjs-dist';
import worker from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
GlobalWorkerOptions.workerSrc = worker;
export class PDFViewer {
  constructor(container, status) {this.container=container; this.status=status; this.page=1;this.zoom=1.1;this.chain=Promise.resolve();}
  async load(url, reset=false) {
    const doc=await getDocument(url).promise;
    const old=this.doc; this.doc=doc;
    if(reset)this.page=1;
    this.page=Math.min(this.page,doc.numPages);
    await this.render();
    if(old) await old.destroy();
  }
  render() {
    this.chain=this.chain.catch(()=>{}).then(async()=>{
      if(!this.doc)return;
      const page=await this.doc.getPage(this.page), viewport=page.getViewport({scale:this.zoom});
      const canvas=document.createElement('canvas'), ratio=Math.min(devicePixelRatio,2);
      canvas.width=viewport.width*ratio;canvas.height=viewport.height*ratio;
      canvas.style.width=`${viewport.width}px`;canvas.style.height=`${viewport.height}px`;
      await page.render({canvasContext:canvas.getContext('2d'),viewport,transform:[ratio,0,0,ratio,0,0]}).promise;
      const wrapper=document.createElement('div');wrapper.className='pdf-page';wrapper.style.width=viewport.width+'px';wrapper.style.height=viewport.height+'px';wrapper.style.setProperty('--scale-factor',this.zoom);
      wrapper.append(canvas);const text=document.createElement('div');text.className='textLayer';wrapper.append(text);
      const layer=new TextLayer({textContentSource:await page.getTextContent(),container:text,viewport});await layer.render();
      this.container.replaceChildren(wrapper);this.status(`${this.page} / ${this.doc.numPages} · ${Math.round(this.zoom*100)}%`);
    });return this.chain;
  }
  async navigate(delta) {if(this.doc){this.page=Math.max(1,Math.min(this.doc.numPages,this.page+delta));await this.render();}}
  async scale(delta) {this.zoom=Math.max(.4,Math.min(2.5,this.zoom+delta));await this.render();}
}
