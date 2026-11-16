# Roadmap

## Etapa 1 — Fundação funcional concluída e validada

Implementado no código:

- FastAPI modular, SQLite e fontes reais no disco.
- Criação/abertura/renomeação/exclusão de projetos, seleção de principal.
- Arquivos e diretórios, mover/renomear/excluir, uploads, busca por nome.
- Importação/exportação ZIP com validação, backup de fontes e metadados.
- CodeMirror 6: LaTeX, linhas, indentação, delimitadores, autocomplete e snippets, busca/substituição, seleção múltipla e histórico por aba.
- Salvamento automático e manual, indicação de pendências e recuperação local após falha.
- pdfLaTeX/latexmk em sandbox com fila, debounce, timeout e logs; BibTeX/Biber conforme documento.
- Prévia PDF.js com página, zoom, download e preservação do PDF válido.
- Temas claro/escuro, divisória redimensionável, layouts editor/PDF, foco e atalhos principais.
- Docker, exemplo abnTeX2 com múltiplos arquivos, testes e documentação em português.

Consulte VALIDATION.md para resultados, em vez de presumir que a presença de um teste significa que ele passou.

## Etapa 2 — Ambiente de pesquisa (parcial)

Implementados com Rascunhos: leitura de artigos do projeto no painel, camada de texto selecionável, última página por navegador, leitura de BibTeX, busca de referências e inserção de citações Markdown. Observações de rascunho vinculam artigo, página e referência. Permanecem: biblioteca global e coleções, terceira área simultânea, busca dentro do PDF, destaques geométricos, favoritos e comentários no código LaTeX com ancoragem por intervalos.

## Etapa 3 — Produtividade (pendente)

Pomodoro por timestamps persistidos em SQLite, pausas, notificações opt-in e estatísticas; notas fora do projeto (a escrita Markdown com associações já existe em Rascunhos); paleta de comandos e busca global; preferências sincronizadas via SQLite; refinamentos de acessibilidade, desempenho e responsividade. O modo de foco e a persistência básica do layout já existem.

## Etapa 4 — Avaliação futura

SyncTeX bidirecional e preservação dos artefatos; histórico/versionamento e conflitos de edição; XeLaTeX/LuaLaTeX; importação/exportação de anotações; Zotero/DOI sem inventar metadados; quotas globais e sandbox em serviço dedicado.

## Limitações conhecidas

- Uso pessoal, local e de um único processo; sem autenticação ou colaboração.
- Preferências e rascunhos vinculados ao navegador; backup de servidor não os inclui.
- Edições externas só entram ao reabrir o arquivo; não há monitoramento ou merge de conflitos.
- Exclusão/movimentação de arquivo principal exige selecionar o novo principal nas configurações.
- Abas preservam histórico na sessão, mas não são restauradas ao reiniciar. Não há fechamento individual de abas nesta versão.
- Logs completos são disponibilizados após terminar o processo, sem streaming incremental.
- O PDF possui canvas e camada de texto selecionável; busca textual e destaques geométricos permanecem pendentes.
- Sem restauração de backup pela interface; restauração é manual.
- Sem reorganização livre de painéis; os três layouts evitam estados difíceis de restaurar.
- Linux e namespaces necessários; Docker Desktop ainda requer validação própria.

## Rascunhos — implementação integrada

Markdown real no projeto; seção no explorador; CRUD, duplicação e pastas; editor CodeMirror com modo Markdown, formatação, busca/substituição, autosave e recuperação; prévia sanitizada com fórmulas; contagem; metadados e estados; LaTeX/artigo ao lado; texto PDF selecionável e última página; observações coloridas com vínculos; referências `.bib`; histórico limitado; prévia Pandoc e inserção confirmada com detecção de conflitos.

Permanecem futuros: biblioteca global e coleções, marcação geométrica no PDF, ancoragem avançada de observações após alterações externas, revisão editorial de diferenças, sincronização entre dispositivos, Pomodoro. O histórico de rascunhos não oferece histórico dos fontes LaTeX; as inserções possuem cópias de segurança do destino no volume.
