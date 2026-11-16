import test from 'node:test';
import assert from 'node:assert/strict';
import {api} from '../src/services/api.js';
test('a API apresenta o erro retornado pelo servidor',async()=>{const previous=globalThis.fetch;try{globalThis.fetch=async()=>({ok:false,json:async()=>({detail:'Caminho inválido'})});await assert.rejects(api('/projects'),/Caminho inválido/);}finally{globalThis.fetch=previous;}});
