# Desenvolvimento

## Ambiente

Python 3.12+, Node 22+ para frontend, TeX Live/latexmk e Bubblewrap para compilação em Linux. A imagem Docker reúne essas dependências. A versão de produção não executa Node.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements-dev.txt
export NEXOTEX_DATA="$PWD/.local-data"
export NEXOTEX_PROJECTS="$PWD/workspace"
PYTHONPATH=backend uvicorn app.main:app --reload
```

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Use o endereço localhost informado pelo Vite. O proxy encaminha `/api` para 8000. Para executar sem Vite, faça `npm run build` e configure `NEXOTEX_STATIC` como o caminho absoluto de `frontend/dist` antes de iniciar o backend.

## Testes

Sem depender de Python/Node no host:

```bash
docker build --target test -t nexotex-test .
docker run --rm --security-opt seccomp=unconfined --security-opt apparmor=unconfined --security-opt no-new-privileges:true nexotex-test
```

Os testes do backend usam SQLite e diretórios temporários. Compilam realmente por Bubblewrap e latexmk: falham se TeX ou namespaces não estiverem disponíveis. Não usam PDF de fixture nem mock de compilador. O teste de persistência reabre o lifespan do serviço mantendo o mesmo diretório. `pytest -v backend/tests` também pode ser executado com PYTHONPATH=backend no host preparado.

```bash
cd frontend
npm test
npm run build
```

O teste unitário do cliente HTTP valida propagação de erros; ele não substitui validação de interface em navegador. Consulte o relatório de validação para a cobertura efetivamente executada.

## Convenções e extensão

Use nomes explícitos, type hints em interfaces novas, validação Pydantic nos corpos e serviços separados das rotas para regras de negócio. Faça toda resolução de caminhos pelo módulo storage. Nunca concatene comandos de shell. Renderize dados do usuário por textContent. Assets devem ser dependências locais do build.

Novos recursos persistentes exigem migração explícita do SQLite, contratos de API, mensagens de erro e testes de integração. A futura camada de comentários deve armazenar intervalos e contexto e mapear mudanças do CodeMirror; somente offsets sem contexto não são suficientes para edições externas. Não alterar fontes LaTeX para armazenar comentários visuais.

## Build e atualização

`docker compose up -d --build` reconstrói código e conserva workspace/volume. Não use `down -v`. O Dockerfile tem targets frontend, runtime, test e production; `production` é o último estágio. A imagem usa versões fixadas de dependências diretas; mantenha o lockfile npm versionado após instalação e revise atualizações deliberadamente.

## Verificação em Chromium

Com a aplicação iniciada:

```bash
docker build -f docker/Dockerfile.browser -t nexotex-browser .
docker run --rm --network host nexotex-browser
```

O teste cria e exclui seu próprio projeto. Verifica edição pelo CodeMirror, gravação via API real, compilação, renderização PDF.js, persistência do tema após recarga, restauração de layout e modo de foco. O parâmetro `--network host` é para o ambiente de testes em Linux; a produção continua publicada somente em localhost.

## Desenvolver Rascunhos

Instale também `pandoc` no host para desenvolvimento sem Docker. As dependências Markdown/KaTeX/DOMPurify e o modo Markdown do CodeMirror estão no package-lock. Os testes de conversão exigem o Pandoc real e verificam que prévias/cancelamentos não alteram o LaTeX, que confirmações são únicas e que alterações concorrentes são recusadas. O teste de navegador específico está em `frontend/tests/drafts.browser.mjs`; execute com a mesma imagem Chromium e monte esse arquivo sobre `/tests/browser.mjs`.

As migrações de metadados são aditivas, em `drafts.init`. Qualquer alteração em rotas comuns de arquivos deve preservar os hooks de rascunhos e o lock compartilhado. O compilador LaTeX não depende de Pandoc nem do módulo de rascunhos.

Exemplo reproduzível do teste Chromium de Rascunhos, com o serviço iniciado:

```bash
docker run --rm --network host \
  -v "$PWD/frontend/tests/drafts.browser.mjs:/tests/browser.mjs:ro" \
  nexotex-browser
```

Para o fluxo original após a introdução do segundo editor, monte `frontend/tests/browser.mjs` da mesma forma. O modo de build também executa cinco testes unitários frontend. As versões fixadas foram auditadas durante a entrega; o relatório npm não apresentou vulnerabilidades após as atualizações.
