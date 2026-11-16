# Validação — 30/10/2026

## Ambiente

Linux, Docker Engine 29.9.2, builder clássico (sem plugin buildx no host), Python 3.12 na imagem, Node 22 no build, TeX Live 2022 do Debian Bookworm, pdfLaTeX, latexmk 4.79 e Biber 2.18. O host não possuía Node, npm, pip ou TeX Live; a construção ocorreu pelos containers.

## Resultados verificados

- Build de produção por Docker Compose: aprovado, com assets locais e usuário não privilegiado.
- Teste unitário do frontend: **1 aprovado**.
- Build Vite: aprovado. O bundle PDF.js ultrapassa 500 KB; o aviso de tamanho não impede o build. Editor e PDF usam chunks separados.
- Backend: **14 testes aprovados em 19,80 s**, com SQLite e arquivos temporários reais e processos TeX reais. Um aviso de depreciação vem da integração Starlette/AnyIO, sem falha funcional.
- Chromium/Playwright: aprovado, sem erros JavaScript. Criação pelo diálogo, digitação no CodeMirror, autosave confirmado pela API, compilação, canvas PDF.js, tema persistido na recarga, layouts restauráveis e foco.
- Healthcheck HTTP: `{"status":"ok"}`.
- Exemplo `examples/academico`: importado via ZIP na API em execução e compilado com abnTeX2, capítulo separado e bibliografia; PDF real de 67.032 bytes.

- Recriação real por `docker compose up -d --no-build --force-recreate`: aprovada; projeto presente no SQLite, fonte idêntico ao exemplo e PDF preservado com 67.032 bytes.
- Segunda execução Chromium: aprovada; captura da interface em `docs/interface.png`.

## Cobertura do backend

Criação e edição de arquivos; reabertura do serviço mantendo SQLite e fontes; path traversal e symlinks; importação/exportação ZIP e backup; rejeição de Zip Slip antes de criar projeto; mover/selecionar principal/excluir; Origin externo e upload binário; documento válido; erro com arquivo/linha e preservação byte a byte do PDF válido; múltiplos arquivos; abnTeX2; BibTeX; Biber; TeX impedido de ler metadados; timeout de loop TeX; coalescência de pedidos de compilação.

Os testes não usam mocks de compilação nem PDFs estáticos como substitutos do fluxo real. O teste unitário do cliente HTTP simula apenas uma resposta de erro.

## Correções orientadas pelos testes

A primeira execução encontrou duas falhas entre 14 testes: abnTeX2 não estava no conjunto de pacotes e BibTeX dependia de `/etc/alternatives` no sandbox. Foram adicionados `texlive-publishers` e o bind somente leitura correspondente. O teste isolado de BibTeX e a suíte completa posterior passaram. Antes disso, o teste de infraestrutura detectou a restrição do Docker a montar procfs: a execução foi ajustada para não expor `/proc`, mantendo os demais namespaces e limites.

## Limites da validação

Não foi validado Docker Desktop, macOS/Windows, dispositivos móveis, carga multiusuário ou todos os pacotes LaTeX existentes. A verificação de navegador cobre o fluxo central; recursos das etapas 2–4 continuam pendentes conforme ROADMAP.md.

## Correção de compatibilidade de modelos importados — 31/10/2026

O modelo importado solicitava `ulem.sty` e, por meio de `easyReview.sty`, `soul.sty`. Os dois arquivos são fornecidos pelo pacote Debian `texlive-plain-generic`, agora incluído explicitamente no Dockerfile. Referência: [lista oficial de arquivos do pacote Debian](https://packages.debian.org/bookworm/all/texlive-plain-generic/filelist).

O teste de regressão compila abnTeX2 carregando ambos os pacotes, com sublinhado, texto riscado e destaque. A suíte completa na imagem corrigida passou: **15 testes aprovados em 21,38 s**, com o mesmo aviso de depreciação Starlette/AnyIO já registrado.

Após resolver as dependências, a compilação real revelou que o modelo carregava simultaneamente `subcaption` e `subfig`. Os capítulos usam ambientes `subfigure` de `subcaption`; o carregamento de `subfig` foi comentado no arquivo local `iftex.cls`. O original foi preservado no mesmo projeto como `iftex.cls.pre-nexotex-fix.bak`. Não houve alteração no conteúdo dos capítulos.

O projeto importado foi compilado com sucesso: **45 páginas**, PDF de **11.584.830 bytes**. O serviço foi atualizado para a imagem reconstruída, conservando os projetos e o volume de dados.

## Rascunhos e tema neutro — 31/10/2026

Implementação integrada à aplicação existente, com Markdown no filesystem, metadados e histórico SQLite, Pandoc 2.17.1.1 para conversão, CodeMirror Markdown, prévia Markdown-it/KaTeX sanitizada e segunda área reutilizada para LaTeX/artigos. O compilador LaTeX existente não foi alterado.

Resultados da imagem final:

- **26 testes backend aprovados em 60,10 s**, usando arquivos, SQLite, Pandoc, TeX Live, BibTeX/Biber e sandbox reais. Permanece apenas o aviso de depreciação da integração Starlette/AnyIO.
- **5 testes frontend aprovados** no build: erros HTTP, offsets Unicode, posição por cursor, inserção antes do fechamento e contagem em português.
- **Chromium — fluxo Rascunhos aprovado:** criar Markdown, editar, autosave confirmado pela API, prévia com fórmula, cancelar sem alterar destino, integrar apenas título selecionado, preservar estado Em revisão, editar o LaTeX ao lado, alternar abas, recuperar uma versão, compilar o resultado, enviar um PDF real para artigos, selecionar texto, salvar observação com página/referência, bloquear HTML e links inseguros e verificar `--bg: #111111`.
- **Chromium — fluxo LaTeX anterior aprovado:** criação, edição, autosave, compilação, PDF.js, tema persistido, layout, foco e recarga. Os seletores do teste foram delimitados ao editor principal agora que existem dois editores.
- Build de produção aprovado; dependências npm fixadas e auditoria após atualização sem vulnerabilidades reportadas.
- Captura do módulo no tema escuro: `docs/rascunhos-dark.png`.

A validação de integração encontrou uma dependência implícita de `hyperref`: o Pandoc gerava âncoras automáticas nos títulos. A conversão passou a desativar esses identificadores automáticos. Um novo teste insere o fragmento e compila o artigo existente sem exigir mudanças no preâmbulo. Identificadores explícitos e links continuam sujeitos aos avisos de `hyperref`.

O serviço principal foi atualizado após criar backup no volume: `/data/backups/antes-rascunhos-1793465219104497457.zip`. Os testes de navegador criaram e excluíram seus próprios projetos, sem alterar os textos acadêmicos existentes.

Limitações: não há biblioteca global de PDFs, destaques geométricos nem Pomodoro nesta versão. Observações ancoram texto por trecho único e artigo por caminho/página. A conversão requer revisão dos avisos de pacotes, imagens, tabelas e macros próprias; nenhuma prévia modifica o documento de destino antes da confirmação.

A recriação real do container também foi aprovada: conteúdo Markdown idêntico, metadados Em revisão, vínculo a main.tex, observação e versão anterior preservados. O ZIP de Backup completo foi aberto e sua cópia SQLite consultada para confirmar metadados e histórico. O projeto temporário foi excluído após a checagem; o serviço final está healthy em localhost:8000.
