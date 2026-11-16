# Guia para agentes de IA — NexoTeX

Este documento dá contexto para contribuir no NexoTeX. Leia também o README e, conforme a tarefa, `docs/ARCHITECTURE.md` e `docs/DEVELOPMENT.md`. As instruções explícitas da pessoa que pediu o trabalho têm prioridade. Respeite as permissões do ambiente e avance nas ações já autorizadas sem pedir confirmações repetidas.

## Objetivo do produto

Ambiente pessoal e local de escrita acadêmica: LaTeX, PDF e rascunhos Markdown. Priorize salvamento confiável, integridade dos trabalhos, compilação real e uma interface discreta. A utilização normal deve funcionar sem nuvem, conta, CDN ou serviços externos. O projeto foi desenvolvido com auxílio do OpenAI Codex; mantenha essa informação no README.

## Antes de alterar

1. Inspecione os arquivos, o estado do Git e as instruções locais. Preserve mudanças existentes.
2. Confira o código real antes de assumir que uma funcionalidade existe. O roadmap registra recursos ainda pendentes.
3. Escolha a menor alteração que resolva o pedido e reutilize os componentes atuais.
4. Se o serviço estiver parado, preserve esse estado ao terminar. Para testar, prefira containers separados com dados temporários; não use trabalhos pessoais como fixtures.

## Mapa do repositório

| Caminho | Responsabilidade |
| --- | --- |
| `backend/app/main.py` | FastAPI, ciclo de vida, proteção de Host/Origin e assets estáticos. |
| `backend/app/api/` | Rotas REST, modelos Pydantic e contratos de entrada. |
| `backend/app/core/storage.py` | SQLite, limites de caminhos, gravação atômica e locks de arquivos. |
| `backend/app/services/projects.py` | Projetos e importação/exportação ZIP. |
| `backend/app/services/compiler.py` | Fila, Bubblewrap, latexmk, logs e publicação do PDF válido. |
| `backend/app/services/drafts.py` | Metadados e versões dos arquivos Markdown. |
| `backend/app/services/conversion.py` | Pandoc, referências e envio confirmado para LaTeX. |
| `frontend/src/main.js` | Composição e fluxo do projeto/editor principal. |
| `frontend/src/components/` | Layout e painel reutilizável para arquivo, artigo e prévia. |
| `frontend/src/editor/` | CodeMirror, modos LaTeX/Markdown e histórico por documento. |
| `frontend/src/pdf/` | PDF.js e camada de texto selecionável. |
| `frontend/src/drafts/` | Interface de rascunhos, observações, referências e prévia sanitizada. |
| `frontend/src/services/` | Cliente HTTP e tratamento de texto/posições. |
| `frontend/src/styles/` | Tokens, temas e estilos compartilhados. |
| `backend/tests/`, `frontend/tests/` | Testes unitários, de integração e de navegador. |
| `examples/academico/` | Exemplo público de abnTeX2, sem dados pessoais. |
| `workspace/` | Documentos locais do usuário; não é código-fonte da aplicação. |

## Regras de dados

- `.tex`, `.bib`, `.md`, imagens e artigos continuam sendo arquivos reais no projeto. Metadados e histórico complementar ficam no SQLite.
- `workspace/`, volumes Docker, `.env`, bancos, backups e documentos pessoais não devem ser adicionados ao Git, exibidos em logs ou usados como dados públicos de exemplo.
- Nunca use `docker compose down -v`, limpe volumes ou apague projetos para resolver um problema de ambiente. Rebuilds devem preservar dados.
- Mudanças de esquema devem ser compatíveis com bancos existentes. A criação das tabelas atuais é idempotente; não recrie o banco durante a inicialização.
- Use `storage.safe` para caminhos e preserve a rejeição de traversal e symlinks. Valide uploads e ZIPs antes de gravar.
- Use gravação atômica e o lock compartilhado. Preserve hashes usados para detectar alterações concorrentes.
- Os hooks das rotas comuns de arquivos atualizam metadados e histórico de rascunhos. Preserve-os ao alterar salvamento, movimentação ou exclusão.

## Compilação e conversão

- Compilação é real: pdfLaTeX/latexmk, BibTeX ou Biber conforme o documento. Nunca troque por PDF estático ou saída simulada.
- Preserve a fila por projeto, o limite de concorrência, a recompilação pendente e o último PDF válido após falha.
- A fila e os locks são locais ao processo. Mantenha um worker Uvicorn; múltiplos workers exigem outra arquitetura de coordenação.
- Preserve Bubblewrap, ausência de rede no sandbox, shell escape desabilitado e limites de CPU, memória, processos, tamanho e tempo. Não adicione fallback sem isolamento.
- Não use `shell=True`, socket Docker, execução privilegiada ou comandos de shell montados com texto do usuário.
- Markdown → LaTeX deve continuar usando Pandoc e seu AST, sem conversor baseado apenas em substituições de strings.
- Enviar para LaTeX exige prévia e confirmação explícita. Preserve o conteúdo anterior/posterior, os hashes, o uso único do token e a cópia do destino anterior. Cancelamento ou erro não devem modificar o destino.
- O rascunho permanece disponível após a inserção. Não marque automaticamente todo o documento como integrado ao enviar um trecho.
- CodeMirror usa posições UTF-16; Python usa pontos de código Unicode. Use os utilitários existentes ao enviar seleções, especialmente com emoji.

## Frontend e experiência

- JavaScript modular, sem framework pesado. Reutilize CodeMirror, PDF.js, o painel existente e os tokens CSS.
- O tema escuro é intencionalmente neutro: fundo `#111111`, superfícies `#181818` e `#222222`. Evite reintroduzir fundos azulados. Mantenha o tema claro legível.
- Preserve autosave, indicação de pendências, recuperação local e histórico independente por documento/painel.
- Markdown renderizado deve continuar sanitizado. Use `textContent` para dados não confiáveis; mantenha as restrições de HTML/URLs e KaTeX sem conteúdo confiável arbitrário.
- Dependências, worker PDF e fontes devem ser empacotados localmente. Node só é necessário para desenvolvimento/build, não em produção.
- Não acrescente botões sem funcionalidade real. Pomodoro, biblioteca global, destaques geométricos em PDF e SyncTeX bidirecional ainda estão pendentes.

## Como verificar

Para documentação, revise caminhos, links, comandos e afirmações contra os arquivos atuais. Não atribua testes antigos à execução atual.

Para mudanças no backend, na compilação ou na conversão:

```bash
docker build --target test -t nexotex-test .
docker run --rm \
  --security-opt seccomp=unconfined \
  --security-opt apparmor=unconfined \
  --security-opt no-new-privileges:true \
  nexotex-test
```

Os testes usam diretórios temporários e processos reais. Não introduza mocks de compilação ou de conversão nos testes de integração.

Para mudanças frontend, com Node 22+:

```bash
cd frontend
npm ci
npm test
npm run build
```

Os testes Chromium e seus comandos estão em `docs/DEVELOPMENT.md`. Eles precisam de uma instância ativa e criam/excluem seus próprios projetos. Use uma instância de teste isolada quando a pessoa tiver pedido para manter o serviço principal parado.

Rode as verificações proporcionais à mudança. Não crie testes que apenas repitam a implementação e não repita suítes sem uma alteração, falha ou dúvida que justifique.

## Entrega

Atualize a documentação quando mudar instalação, uso, persistência ou contratos. Informe o que mudou, como foi verificado e os limites restantes, em português claro. Nunca apresente recursos pendentes como implementados.

Antes de publicar, revise `git diff --cached` e a lista de arquivos. Envie apenas o código e os exemplos públicos. Preserve o histórico remoto e não use force push sem autorização explícita.
