import {defineConfig} from 'vite';
export default defineConfig({build:{rollupOptions:{output:{manualChunks:{editor:['codemirror','@codemirror/legacy-modes/mode/stex'],pdf:['pdfjs-dist']}}}},server:{proxy:{'/api':'http://127.0.0.1:8000'}}});
