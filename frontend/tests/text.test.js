import test from 'node:test';
import assert from 'node:assert/strict';
import {codePointOffset,countText,insertionPosition} from '../src/services/text.js';
test('offsets Unicode preservam a posição após emoji e acentos',()=>{assert.equal(codePointOffset('💡ação',2),1);assert.equal(insertionPosition('💡\ntexto','line',2),2);});
test('inserção por cursor exige contexto explícito',()=>{assert.throws(()=>insertionPosition('texto','cursor'),/Abra o arquivo/);assert.equal(insertionPosition('💡abc','cursor',1,2),1);});
test('inserção preserva o fechamento do documento',()=>{assert.equal(insertionPosition('texto\n\\end{document}','before-end'),6);assert.throws(()=>insertionPosition('texto','line',9),/inválida/);});
test('contagem aceita texto acadêmico em português',()=>{assert.deepEqual(countText('Uma hipótese — ação 💡'),{words:3,characters:21});});
