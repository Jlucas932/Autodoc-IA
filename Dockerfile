# ============================================================================
# AutoDocIA v2.0 - Dockerfile Multi-Stage (simplificado, sem wheels)
# ============================================================================

# Stage 1 - builder (opcional, apenas para compilar dependências pesadas se precisar)
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    make \
    libpq-dev \
    default-libmysqlclient-dev \
    unixodbc-dev \
    curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt

# Apenas valida se requirements.txt está correto (instala aqui, mas não será usado no runtime)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt


# ============================================================================
# Stage 2 - runtime (imagem final que roda em produção)
# ============================================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    unixodbc \
    curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements e instalar dependências no runtime
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copiar código da aplicação
COPY . /app

# Configurar PYTHONPATH para imports absolutos
ENV PYTHONPATH="/app/src/main/python:${PYTHONPATH}"

# Criar diretórios necessários
RUN mkdir -p /app/logs /app/rag/index /app/knowledge/etps/raw /app/knowledge/etps/parsed

# Expor porta
EXPOSE 5002

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5002/api/health || exit 1

# CMD de produção com gunicorn
CMD ["gunicorn", "-c", "gunicorn.conf.py", "--bind", "0.0.0.0:5002", "src.main.python.applicationApi:app"]
