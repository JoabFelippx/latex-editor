# Rascunhos

[Voltar ao README](../README.md)

A seção **Rascunhos** fica no explorador do projeto. Clique em **+** para criar um arquivo, por exemplo `rascunhos/introducao.md`. Caminhos como `rascunhos/capitulo-1/ideias.md` criam as pastas necessárias. O menu **···** permite renomear/mover, duplicar e excluir. A busca dessa seção procura no nome, título e conteúdo; rascunhos abrem nas mesmas abas dos arquivos LaTeX.

Escreva em Markdown: `# Título`, `## Subtítulo`, `**negrito**`, `*itálico*`, listas `- item`, tarefas `- [ ] revisar`, citações `> texto`, links `[nome](endereço)` e fórmulas `$E=mc^2$` ou `$$...$$`. Use Ctrl+B/Ctrl+I para formatar; busca, substituição e histórico de desfazer continuam no CodeMirror. O salvamento automático usa o fluxo existente, e o ponto na aba indica conteúdo pendente. A barra do rascunho mostra palavras, caracteres e estado (Ideia, Em desenvolvimento, Em revisão ou Integrado).

**Prévia** abre a visualização Markdown no painel ao lado, com fórmulas renderizadas por KaTeX. **Detalhes** permite associar um arquivo `.tex`, indicar uma seção e abrir o LaTeX ao lado. O estado é manual e nunca bloqueia a escrita. O seletor do painel alterna entre PDF compilado, arquivo, artigo e prévia, mantendo a divisória redimensionável.

### Consultar artigos e referências

Envie um PDF pelo **Upload**, por exemplo em `artigos/artigo.pdf` (limite individual existente: 10 MB). Abra-o no explorador ou escolha **Artigo PDF** no painel. É possível navegar por páginas, ajustar zoom, selecionar/copiar texto e retornar à última página neste navegador. Essa versão aproveita arquivos do projeto; não existe ainda uma biblioteca global de artigos nem integração Zotero.

Com o rascunho aberto, selecione texto no artigo e use **Detalhes → + Observação**. O diálogo recebe o trecho, artigo e página e permite registrar uma ideia, pendência de referência, dúvida, revisão ou tarefa. Cada observação tem cor personalizável e pode ser editada, excluída ou usada para voltar à página do artigo. Uma seleção no rascunho também pode ficar vinculada à observação. Os vínculos usam o trecho textual; após edições extensas ou repetições, pode ser necessário atualizar o contexto na observação. Não são marcações de regiões dentro do PDF.

**Referências** lê os `.bib` reais do projeto e busca autor, título ou chave, inserindo citações Markdown `[@chave]`. Em observações, também é possível associar uma entrada existente. Links internos inseridos nos blocos de observação usam `/nexotex/pdf?path=...&page=...`; a prévia abre o artigo correspondente. Os metadados bibliográficos são lidos dos arquivos e não são gerados automaticamente.

### Enviar para LaTeX com confirmação

1. Selecione um trecho do rascunho ou deixe para converter o documento inteiro.
2. Clique em **Enviar para LaTeX**, escolha o `.tex` de destino e a posição: início, fim, antes do fechamento do documento, linha indicada ou cursor do arquivo aberto no painel lateral.
3. Clique em **Gerar prévia** e confira o LaTeX convertido, o contexto da inserção e os avisos de pacotes.
4. Clique em **Confirmar inserção**. **Cancelar** fecha o diálogo sem alterar o destino.

A conversão usa Pandoc com estrutura de Markdown, incluindo títulos, listas, ênfase, fórmulas, links e citações. Produz somente um fragmento, sem preâmbulo ou documento novo. A detecção de citações distingue abnTeX2, natbib, biblatex e `\cite` comum; o diálogo permite escolher explicitamente. Confira a configuração se o projeto usa macros próprias.

A inserção preserva os trechos anteriores e posteriores à posição escolhida. Um hash impede aplicar uma prévia se o destino ou o rascunho tiver mudado; gere outra prévia nesse caso. Há uma cópia de segurança do destino em `/data/transfer-backups/<projeto>/<token>.tex`. O rascunho original permanece disponível e seu estado não é alterado automaticamente, mesmo no envio completo. Observações guardadas só nos metadados não são enviadas. Um bloco Markdown inserido explicitamente no texto passa a fazer parte do conteúdo convertido.

### Versões, recuperação e armazenamento

**Versões → Guardar versão agora** cria um ponto de recuperação. A primeira alteração preserva o texto anterior; durante a escrita são guardadas no máximo uma versão automática a cada cinco minutos, além dos pontos de integração/restauração. Cada rascunho conserva até 50 versões. É possível visualizar uma versão antes de restaurá-la; o conteúdo atual é guardado antes da restauração. Rascunhos excluídos e seus históricos são removidos: faça um backup completo antes de excluir material importante.

O conteúdo atual é um arquivo `.md` real dentro do projeto. SQLite guarda título, datas, estado, associações, observações e versões antigas. Esses dados sobrevivem a rebuilds e reinicializações e entram no **Backup completo** existente. **Exportar ZIP** contém os arquivos, mas não os metadados nem o histórico SQLite. Rascunhos não são incluídos automaticamente no documento LaTeX.

Alterações ainda não salvas também possuem recuperação no navegador, inclusive no painel lateral. Se um editor externo modificar um arquivo aberto, o salvamento com hash evita sobrescrevê-lo silenciosamente; reconcilie as alterações e reabra o arquivo. Notas de pesquisa, versões e backups de integração usam espaço em disco; mantenha backups regulares.

Limitações: a conversão preserva estrutura, não formatação visual idêntica. Links precisam de `hyperref`; tabelas podem exigir `longtable`, `booktabs` e `array`; checklists podem precisar de `amssymb`. Caminhos de imagens e macros LaTeX devem ser revisados. A prévia não substitui a compilação. O Pomodoro e a biblioteca global de artigos continuam pendentes; o módulo não adiciona controles simulados para esses recursos.

Para preservar os vínculos e versões, renomeie/mova rascunhos pelo explorador do NexoTeX. Renomeações externas não atualizam os metadados automaticamente. As cópias históricas de destinos em `/data/transfer-backups` ficam no volume e precisam ser copiadas separadamente se quiser preservá-las fora dele; o Backup completo exporta os fontes atuais e o SQLite.
