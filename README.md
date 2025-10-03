# AutoDocIA v2.0 - Sistema de Geração Inteligente de ETPs

Sistema inteligente para geração automatizada de Estudos Técnicos Preliminares (ETPs) com suporte a múltiplos SGBDs, segurança on-premise, fluxo consultivo RAG e observabilidade completa.

## 🆕 Novidades da Versão 2.0

### Suporte Multi-SGBD Cross-Database
- **PostgreSQL** (recomendado para produção)
- **MySQL/MariaDB**
- **SQL Server** (via pyodbc)
- **SQLite** (desenvolvimento)
- Pool de conexões com `pool_pre_ping=True`
- Retry logic e timeouts configuráveis

### Fluxo Consultivo RAG
- IA atua como **consultora de ETP**, não como geradora automática
- Prioriza **base de conhecimento** (RAG) antes de sugerir requisitos
- Iteração item a item com comandos em português natural
- **Sugestão de caminhos** quando necessidade é ambígua (compra vs locação vs comodato)
- Citações de documentos de origem
- **Fallback robusto**: funciona sem FAISS (BM25 puro)

### Segurança On-Premise
- Headers de segurança (CSP, X-Frame-Options, etc.)
- CORS configurável por ambiente
- Rate limiting configurável
- Mascaramento de segredos em logs
- Validação rigorosa de uploads
- Timeouts em chamadas externas

### Observabilidade Completa
- Logs estruturados em JSON
- Request ID para correlação
- Métricas Prometheus (contadores e histogramas)
- Endpoint `/metrics` protegido por token
- Healthchecks

### Performance e Escalabilidade
- Pool de conexões configurável
- Índices portáveis (multi-SGBD)
- FAISS no filesystem (não no banco)
- Cache LRU in-process
- Gunicorn workers

## 📋 Requisitos

- Python 3.11+
- PostgreSQL 13+ / MySQL 8+ / SQL Server 2019+ / SQLite 3.35+
- OpenAI API Key (opcional para modo offline)
- Docker e Docker Compose (opcional)

## 🚀 Instalação

### 1. Clonar o repositório

```bash
git clone <repository-url>
cd autodoc-ia-fixed
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Edite `.env` e configure:

```bash
# Banco de dados (escolha um)
DATABASE_URL=postgresql://user:password@localhost:5432/autodoc_ia
# DATABASE_URL=mysql://user:password@localhost:3306/autodoc_ia
# DATABASE_URL=mssql+pyodbc://user:password@localhost:1433/autodoc_ia?driver=ODBC+Driver+17+for+SQL+Server
# DATABASE_URL=sqlite:///./autodoc_ia.db

# OpenAI (opcional)
OPENAI_API_KEY=sk-proj-your-api-key-here

# Secret Key (OBRIGATÓRIO)
SECRET_KEY=your-secret-key-here-change-in-production

# Pool de conexões
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=1800

# Segurança
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5000
RATE_LIMIT_PER_MINUTE=30
REQUEST_MAX_MB=5

# Métricas
METRICS_TOKEN=your-metrics-token-here

# RAG
RAG_FAISS_PATH=rag/index/faiss
RAG_TOPK=5

# Logging
LOG_LEVEL=INFO
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Criar banco de dados

#### PostgreSQL
```bash
createdb autodoc_ia
```

#### MySQL
```bash
mysql -u root -p -e "CREATE DATABASE autodoc_ia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

#### SQL Server
```sql
CREATE DATABASE autodoc_ia;
```

### 5. Executar migrações

```bash
# Aplicar migrações
alembic upgrade head
```

### 6. Ingerir base de conhecimento

```bash
# Colocar PDFs em knowledge/etps/raw/
# Executar ingestão
python -m src.main.python.rag.ingest_etps --rebuild
```

### 7. Executar aplicação

#### Desenvolvimento
```bash
python src/main/python/applicationApi.py
```

#### Produção
```bash
gunicorn -c gunicorn.conf.py src.main.python.applicationApi:app
```

## 🐳 Docker

### Desenvolvimento

```bash
docker-compose --profile dev up
```

### Produção

```bash
docker-compose --profile prod up -d
```

## 📚 Uso da API

### 1. Iniciar sessão

```bash
POST /api/etp-dynamic/session/start
```

### 2. Informar necessidade

```bash
POST /api/etp-dynamic/suggest-requirements
{
  "necessity": "Precisamos de 3 veículos para a secretaria de saúde"
}
```

### 3. Revisar requisitos

```bash
POST /api/etp-dynamic/review-requirements
{
  "session_id": "...",
  "user_message": "remova o 2 e troque o 4"
}
```

Comandos suportados:
- **Remover**: "remova 2", "exclui 3 e 5", "apaga do 2 ao 4"
- **Trocar**: "troque o 3", "refaz 1 e 4", "substitui 2"
- **Manter apenas**: "mantém apenas 1, 3 e 5", "quero só 2 e 4"
- **Confirmar**: "confirmo", "ok", "está bom"

### 4. Verificar ambiguidade (automático)

```bash
POST /api/etp-dynamic/options-if-ambiguous
{
  "session_id": "..."
}
```

### 5. Escolher opção

```bash
POST /api/etp-dynamic/pick-option
{
  "session_id": "...",
  "option_id": "opt_locacao"
}
```

## 🔧 Configuração Avançada

### Pool de Conexões

```bash
DB_POOL_SIZE=5           # Número de conexões no pool
DB_MAX_OVERFLOW=10       # Conexões extras permitidas
DB_POOL_RECYCLE=1800     # Reciclar conexões após 30min
```

### Rate Limiting

```bash
RATE_LIMIT_PER_MINUTE=30
RATE_LIMIT_PER_HOUR=500
RATE_LIMIT_PER_DAY=2000
```

### Gunicorn

```bash
GUNICORN_WORKERS=4       # Número de workers
GUNICORN_THREADS=2       # Threads por worker
GUNICORN_BIND=0.0.0.0:5000
GUNICORN_TIMEOUT=120
```

## 📊 Monitoramento

### Healthcheck

```bash
GET /api/health
```

### Métricas Prometheus

```bash
GET /metrics
Authorization: Bearer <METRICS_TOKEN>
```

Métricas disponíveis:
- `http_requests_total{endpoint, method, status}` - Total de requisições
- `http_request_latency_seconds{endpoint, method}` - Latência das requisições

## 🐛 Troubleshooting

### pool_pre_ping

**Problema**: Conexões quebradas causando erros.

**Solução**: `pool_pre_ping=True` está ativado por padrão no DatabaseConfig.py. Verifica conexões antes de usar.

### Alembic

**Problema**: Erro ao executar migrações.

**Solução**:
```bash
# Verificar DATABASE_URL
echo $DATABASE_URL

# Verificar se o banco existe
# PostgreSQL: psql -l
# MySQL: mysql -e "SHOW DATABASES;"

# Executar migração manualmente
alembic upgrade head
```

### BM25 Fallback

**Problema**: FAISS não disponível.

**Solução**: O sistema usa BM25 automaticamente quando FAISS não está disponível. Verifique logs:
```
⚠️ FAISS ausente, usando BM25 somente
```

Para construir índice FAISS:
```bash
python -m src.main.python.rag.ingest_etps --rebuild
```

### CORS

**Problema**: Erro de CORS no frontend.

**Solução**: Configure `CORS_ALLOWED_ORIGINS` no .env:
```bash
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://app.example.com
```

### Limites de Upload

**Problema**: Erro ao fazer upload de arquivo grande.

**Solução**: Ajuste `REQUEST_MAX_MB` no .env:
```bash
REQUEST_MAX_MB=10  # 10 MB
```

### Máscaras de Segredos nos Logs

**Problema**: Segredos aparecendo nos logs.

**Solução**: Use as funções de máscara:
```python
from utils.security import mask_key, mask_url

masked_key = mask_key(api_key)
masked_url = mask_url(database_url)
logger.info(f"API Key: {masked_key}")
```

## 📝 Estrutura do Projeto

```
autodoc-ia-fixed/
├── src/main/python/
│   ├── adapter/entrypoint/       # Controllers (rotas)
│   ├── application/config/       # Configuração Flask
│   ├── domain/
│   │   ├── dto/                  # Modelos de dados
│   │   ├── interfaces/           # Interfaces (DB, etc.)
│   │   └── usecase/etp/          # Lógica de negócio
│   ├── rag/                      # RAG e ingestão
│   └── utils/                    # Utilitários (security, etc.)
├── alembic/                      # Migrações de banco
│   └── versions/                 # Arquivos de migração
├── knowledge/etps/               # Base de conhecimento
│   ├── raw/                      # PDFs originais
│   └── parsed/                   # JSONLs processados
├── rag/index/                    # Índices FAISS e BM25
├── logs/                         # Logs da aplicação
├── static/                       # Frontend
├── templates/                    # Templates HTML
├── .env.example                  # Exemplo de configuração
├── requirements.txt              # Dependências Python
├── Dockerfile                    # Imagem Docker (multi-stage)
├── docker-compose.yml            # Orquestração Docker
├── gunicorn.conf.py              # Configuração Gunicorn
├── alembic.ini                   # Configuração Alembic
└── README.md                     # Este arquivo
```

## 🔒 Segurança

- **Nunca** commite `.env` com credenciais reais
- Use SECRET_KEY forte em produção
- Configure CORS_ALLOWED_ORIGINS adequadamente
- Use HTTPS em produção
- Mantenha dependências atualizadas
- Revise logs regularmente
- Proteja endpoint `/metrics` com token forte

## 📄 Licença

[Especificar licença]

## 👥 Contribuindo

[Instruções para contribuição]

## 📞 Suporte

[Informações de contato/suporte]
