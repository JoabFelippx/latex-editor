# Arquitetura

## Componentes e responsabilidades

Um processo Uvicorn/FastAPI serve a API REST e os assets estáticos gerados pelo Vite. Node só participa do build e do desenvolvimento. CodeMirror 6 e PDF.js são empacotados localmente, inclusive o worker PDF; não há CDN na interface.

- `backend/app/api/routes.py`: contratos HTTP e validação Pydantic.
- `backend/app/core/storage.py`: diretórios configuráveis, limites de caminho, SQLite e gravações atômicas.
- `backend/app/services/projects.py`: criação, árvore e arquivos ZIP.
- `backend/app/services/compiler.py`: fila, sandbox, processo TeX e publicação de PDF.
- `frontend/src/editor/`: editor, snippets, estados independentes de abas.
- `frontend/src/pdf/`: renderização de páginas, zoom e navegação.
- `frontend/src/services/`: cliente HTTP e mensagens de falha.
- `frontend/src/main.js`: composição da interface e fluxo da primeira versão.

O frontend usa JS modular sem framework. A interface oferece explorador, abas, editor e PDF, terminal, temas, três layouts e foco. Os próximos módulos devem separar os fluxos de pesquisa e produtividade deste controlador.

## Dados e persistência

SQLite armazena ID, nome e arquivo principal de cada projeto. Os fontes são arquivos UTF-8 reais sob `NEXOTEX_PROJECTS/<id>`; outros arquivos são preservados binariamente. `NEXOTEX_DATA` contém o banco e `builds/<id>/document.pdf`. Os IDs são gerados pelo servidor, sem derivar caminhos do nome do projeto. PUT grava em temporário e troca atomicamente; não há controle de versões ou conflitos entre editores externos.

A API de backup usa SQLite Backup para metadados. O ZIP completo inclui fontes e metadados; não é uma transação de todos os arquivos. Interrompa a edição durante o backup. Preferências do navegador e rascunhos usam localStorage nesta etapa. SQLite será ampliado nas etapas seguintes para anotações, notas e sessões.

## Compilação

1. O cliente conclui o salvamento antes de solicitar POST `/api/projects/{id}/compile`.
2. O servidor cria uma tarefa assíncrona e retorna 202. GET na mesma rota informa fila, execução, log, erros e versão do PDF. Polling a cada 800 ms enquanto há trabalho evita WebSocket desnecessário.
3. Cada projeto tem uma tarefa ativa e um indicador de recompilação pendente. Pedidos repetidos durante execução se fundem em um único próximo build. Até dois projetos compilam ao mesmo tempo. Use **apenas um worker Uvicorn** nesta arquitetura: a fila é local ao processo.
4. O projeto é copiado para um diretório temporário limitado a 100 MB; a cópia evita que latexmk grave auxiliares nos fontes. Mudanças externas durante a cópia não têm snapshot transacional.
5. Bubblewrap cria namespaces sem rede, expondo dependências TeX somente leitura e a cópia como `/work`. Não monta `/proc`, evitando a restrição de procfs mascarado do Docker. `/etc/alternatives` é exposto somente leitura para resolver executáveis Debian como BibTeX. Ambiente limpo, shell escape desabilitado, `latexmk -norc`, timeout, CPU, memória, processos e tamanho de arquivo limitados. Não se usa shell=True.
6. latexmk executa pdfLaTeX e detecta BibTeX/Biber a partir dos auxiliares. SyncTeX é habilitado, mas a navegação fonte/PDF não está integrada e o arquivo SyncTeX ainda não é preservado.
7. Apenas saída com retorno zero e PDF existente substitui atomicamente o PDF publicado. Em erro, o último PDF permanece. O log é limitado aos últimos 500 KB e erros no formato `arquivo.tex:linha:` são estruturados.
8. Temporários são removidos. Na finalização do serviço as tarefas são canceladas e grupos de processos ativos recebem SIGKILL.

A prévia PDF.js mantém página e zoom ao atualizar. Renderizações são sequenciais para evitar conflitos no canvas. A camada de texto agora permite selecionar e copiar conteúdo no PDF compilado e nos artigos. Busca textual, links do próprio PDF e destaques geométricos permanecem pendentes.

## Segurança e limites

O serviço usa usuário não privilegiado, porta publicada somente no loopback, validação de Host e Origin, bloqueio de symlinks e caminhos absolutos/traversal. ZIPs têm limite comprimido de 25 MB, expandido de 100 MB e 2000 entradas; links e criptografia são rejeitados. Uploads individuais têm limite configurável de 10 MB. Não exponha o serviço à rede sem autenticação e revisão de segurança.

O Compose usa `seccomp=unconfined` e `apparmor=unconfined` para permitir namespaces de usuário do Bubblewrap, além de no-new-privileges. Isso amplia a superfície de chamadas do serviço: o sandbox interno não é uma VM e depende do kernel. Não se usa privileged, Docker socket ou capacidades adicionais. Hosts que proíbem user namespaces falham de forma explícita; não executamos TeX sem sandbox como alternativa. Para documentos hostis, utilize uma VM descartável. Bibliotecas TeX e parsers podem ter falhas; isolamento não é garantia absoluta. Limites de processo não substituem quota de disco global.

A ausência de autenticação é uma escolha para uso pessoal local, não multiusuário. A interface não interpola nomes de arquivos em HTML; elementos dinâmicos usam textContent. PDFs são servidos como application/pdf e o middleware aplica nosniff e bloqueio de framing.

## Referências técnicas

- [FastAPI em containers](https://fastapi.tiangolo.com/deployment/docker/)
- [Exemplos PDF.js](https://mozilla.github.io/pdf.js/examples/)
- [CodeMirror](https://codemirror.net/docs/)

## Módulo Rascunhos

`services/drafts.py` mantém Markdown no filesystem e metadados nas tabelas aditivas `drafts`, `draft_versions` e `draft_transfers`. A inicialização é idempotente e conserva bancos existentes. As conexões ativam foreign keys; exclusões de projeto removem metadados dependentes. As rotas de arquivo existentes delegam gravações `.md` ao serviço, preservando autosave, histórico e acesso externo. Movimentações pelo explorador atualizam caminhos e vínculos LaTeX; links internos de artigos inseridos manualmente no Markdown não são reescritos ao mover arquivos.

`services/conversion.py` usa Pandoc local com entrada padrão, sandbox, memória/CPU/timeout limitados e saída textual. O Markdown passa pelo AST JSON; nós de citação são adaptados ao estilo do projeto sem inventar chaves. Nós de matemática permanecem no AST. O writer LaTeX produz fragmentos; não usa standalone ou templates. Código com sintaxe é emitido sem macros de realce. Avisos indicam pacotes necessários para estruturas mais complexas.

A prévia cria um token temporário de 30 minutos com hash do rascunho e do destino, posição Unicode, trecho convertido e contexto. A aplicação exige confirmação explícita, compara novamente os hashes e insere sob lock compartilhado com o salvamento comum. O token só pode ser usado uma vez. A cópia do destino anterior fica no volume de dados. Escritas em arquivos e transações SQLite não são uma transação única do sistema operacional: uma interrupção abrupta pode requerer inspeção do backup, mas uma prévia antiga não deve ser reaplicada contra um destino alterado. Editores externos não participam dos locks do processo.

O frontend mantém `main.js` como composição do fluxo de projeto. `components/shell.js` contém o layout anterior; `components/research-panel.js` reutiliza a segunda área para arquivos, artigos e prévia, com editor e autosave independentes. `drafts/controller.js` conecta explorador, metadados, observações, referências, versões e confirmação. `drafts/markdown.js` renderiza Markdown sem HTML arbitrário, aplica KaTeX e sanitização DOMPurify, com fontes locais. Não há segundo sistema de navegação.

PDF.js renderiza agora uma camada de texto selecionável sobre o canvas. Os artigos são PDFs reais do projeto, acessados por uma rota confinada ao workspace; não há cópia para outra biblioteca. Observações armazenam página, caminho e trecho, sem prometer destaques geométricos em PDFs. A busca bibliográfica lê `.bib` com o parser de Pandoc e fornece apenas os dados presentes. Arquivos inválidos ou muito grandes não entram na lista bibliográfica.

As posições do CodeMirror usam UTF-16; o contrato da conversão usa pontos de código Unicode, com conversão explícita no frontend. Histórico e testes cobrem emoji, acentos, cancelamento e conflitos. Cores e tipografia reutilizam os tokens; superfícies dark passam a cinzas neutros (#111111, #181818 e #222222).
