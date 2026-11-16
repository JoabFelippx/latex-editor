FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build && npm test

FROM python:3.12-slim-bookworm AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends latexmk texlive-latex-extra texlive-lang-portuguese texlive-fonts-recommended texlive-science texlive-bibtex-extra biber bubblewrap util-linux lmodern && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends texlive-publishers && rm -rf /var/lib/apt/lists/*
RUN groupadd -g 1000 nexotex && useradd -m -u 1000 -g nexotex nexotex && mkdir /data /workspace && chown nexotex:nexotex /data /workspace
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=frontend /build/dist ./static
ENV NEXOTEX_DATA=/data NEXOTEX_PROJECTS=/workspace PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# ulem.sty is distributed in plain-generic, not latex-extra, on Debian.
RUN apt-get update && apt-get install -y --no-install-recommends texlive-plain-generic pandoc && rm -rf /var/lib/apt/lists/*
USER nexotex
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS test
USER root
COPY backend/requirements-dev.txt ./requirements-dev.txt
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY backend/tests ./tests
USER nexotex
CMD ["python", "-m", "pytest", "-v", "-p", "no:cacheprovider", "tests"]

FROM runtime AS production
