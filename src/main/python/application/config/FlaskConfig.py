"""
Configuração Flask com suporte multi-SGBD, segurança on-premise e observabilidade.
"""
import os
import logging
import json
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, send_from_directory, request, g, Response, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import uuid
import time

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("prometheus_client não instalado. Métricas desabilitadas.")

# Carregar variáveis de ambiente
load_dotenv()

# Inicializar métricas Prometheus
if PROMETHEUS_AVAILABLE:
    REQ_COUNT = Counter(
        "http_requests_total",
        "Total de requisições HTTP",
        ["endpoint", "method", "status"]
    )
    REQ_LATENCY = Histogram(
        "http_request_latency_seconds",
        "Latência das requisições HTTP",
        ["endpoint", "method"]
    )
else:
    REQ_COUNT = None
    REQ_LATENCY = None

# Configurar logging estruturado
def setup_structured_logging():
    """Configura logging estruturado em formato JSON."""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    class JSONFormatter(logging.Formatter):
        """Formatter para logs em JSON."""
        def format(self, record):
            log_data = {
                'timestamp': self.formatTime(record, self.datefmt),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'request_id': getattr(record, 'request_id', None),
            }
            
            if record.exc_info:
                log_data['exception'] = self.formatException(record.exc_info)
            
            return json.dumps(log_data, ensure_ascii=False)
    
    # Criar diretório de logs se não existir
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Configurar handlers
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler('logs/app.log', mode='a')
    
    # Aplicar formatter JSON
    json_formatter = JSONFormatter()
    console_handler.setFormatter(json_formatter)
    file_handler.setFormatter(json_formatter)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return root_logger

logger = setup_structured_logging()


def mask_secret(value: str, show_chars: int = 4) -> str:
    """
    Mascara segredos para logging seguro.
    
    Args:
        value: Valor a ser mascarado
        show_chars: Número de caracteres a mostrar no final
    
    Returns:
        String mascarada
    """
    if not value or len(value) <= show_chars:
        return "****"
    return f"****{value[-show_chars:]}"


def validate_environment_variables():
    """Valida as variáveis de ambiente obrigatórias."""
    required_vars = {
        'SECRET_KEY': 'Chave secreta do Flask é obrigatória',
        'DATABASE_URL': 'URL do banco de dados é obrigatória (PostgreSQL, MySQL, MSSQL, SQLite)',
    }
    
    # OpenAI é opcional (para modo offline)
    optional_vars = {
        'OPENAI_API_KEY': 'Chave da API OpenAI (opcional para modo offline)',
    }
    
    missing_vars = []
    for var, message in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var}: {message}")
    
    if missing_vars:
        raise ValueError(f"Variáveis de ambiente obrigatórias faltando:\n" + "\n".join(missing_vars))
    
    # Log de configuração (mascarado)
    db_url = os.getenv('DATABASE_URL', '')
    db_dialect = db_url.split('://')[0].split('+')[0] if '://' in db_url else 'unknown'
    
    logger.info(f"✅ Configuração validada - DB: {db_dialect}, Embeddings: {os.getenv('EMBEDDINGS_PROVIDER', 'openai')}")
    
    # Avisar sobre variáveis opcionais faltando
    for var, message in optional_vars.items():
        if not os.getenv(var):
            logger.warning(f"⚠️ {message}")


def get_config_values():
    """Retorna valores de configuração validados."""
    return {
        'database_url': os.environ['DATABASE_URL'],
        'embeddings_provider': os.getenv('EMBEDDINGS_PROVIDER', 'openai'),
        'lexml_timeout': int(os.getenv('LEXML_TIMEOUT_SECONDS', '8')),
        'rag_topk': int(os.getenv('RAG_TOPK', '5')),
        'rag_faiss_path': os.getenv('RAG_FAISS_PATH', 'rag/index/faiss'),
        'legal_cache_ttl': int(os.getenv('LEGAL_CACHE_TTL_DAYS', '7')),
        'rate_limit_per_minute': int(os.getenv('RATE_LIMIT_PER_MINUTE', '30')),
        'request_max_mb': int(os.getenv('REQUEST_MAX_MB', '5')),
        'cors_allowed_origins': os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if os.getenv('CORS_ALLOWED_ORIGINS') else [],
    }


def auto_load_knowledge_base():
    """
    Verifica se a base de conhecimento está vazia e executa a ingestão automaticamente se necessário.
    Esta função deve ser chamada após a inicialização do banco de dados.
    """
    from domain.interfaces.dataprovider.DatabaseConfig import db
    from domain.dto.KbDto import KbDocument, KbChunk
    
    try:
        # Verificar se existem documentos na base
        document_count = db.session.query(KbDocument).count()
        chunk_count = db.session.query(KbChunk).count()
        
        if document_count > 0:
            # Base já populada
            logger.info(f"📚 Base de conhecimento já populada com {document_count} documentos e {chunk_count} chunks")
            return True
        
        # Base vazia, logar instrução para ingestão manual
        logger.warning("⚠️ Base de conhecimento vazia. Execute: python -m rag.ingest_etps --rebuild")
        return False
            
    except Exception as e:
        logger.error(f"❌ Erro verificando base de conhecimento: {str(e)}")
        return False


def add_security_headers(response):
    """Adiciona headers de segurança às respostas."""
    # Content Security Policy (sem unsafe-inline)
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'"
    )
    
    # Outros headers de segurança
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    return response


def add_request_id():
    """Adiciona request_id para correlação de logs."""
    g.request_id = str(uuid.uuid4())
    g.start_time = time.time()


def log_request():
    """Loga informações da requisição."""
    if request.path.startswith('/static'):
        return  # Não logar arquivos estáticos
    
    duration = time.time() - g.get('start_time', time.time())
    
    log_data = {
        'request_id': g.get('request_id'),
        'method': request.method,
        'path': request.path,
        'status': 'started',
        'ip': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'unknown')[:100],
    }
    
    logger.info(f"Request: {json.dumps(log_data, ensure_ascii=False)}")


def log_response(response):
    """Loga informações da resposta e registra métricas."""
    if request.path.startswith('/static'):
        return response  # Não logar arquivos estáticos
    
    duration = time.time() - g.get('start_time', time.time())
    endpoint = request.endpoint or "unknown"
    
    log_data = {
        'request_id': g.get('request_id'),
        'method': request.method,
        'path': request.path,
        'status': response.status_code,
        'duration_ms': round(duration * 1000, 2),
        'size_bytes': response.content_length or 0,
    }
    
    logger.info(f"Response: {json.dumps(log_data, ensure_ascii=False)}")
    
    # Registrar métricas Prometheus
    if PROMETHEUS_AVAILABLE and REQ_COUNT and REQ_LATENCY:
        try:
            REQ_COUNT.labels(endpoint=endpoint, method=request.method, status=response.status_code).inc()
            REQ_LATENCY.labels(endpoint=endpoint, method=request.method).observe(duration)
        except Exception as e:
            logger.warning(f"Erro ao registrar métricas: {str(e)}")
    
    return response


def create_api():
    """Cria e configura a aplicação Flask."""
    
    # Validar variáveis de ambiente obrigatórias
    validate_environment_variables()
    
    # Obter valores de configuração
    config = get_config_values()
    
    # Caminho absoluto da pasta atual
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # Encontrar a pasta static corretamente
    # De: src/main/python/application/config/
    # Para: static/ (na raiz do projeto)
    static_path = os.path.join(basedir, '..', '..', '..', '..', '..', 'static')
    static_path = os.path.abspath(static_path)
    
    # Encontrar a pasta templates corretamente
    # De: src/main/python/application/config/
    # Para: templates/ (na raiz do projeto)
    template_path = os.path.join(basedir, '..', '..', '..', '..', '..', 'templates')
    template_path = os.path.abspath(template_path)
    
    logger.info(f"📁 Pasta static configurada: {static_path}")
    logger.info(f"📁 Pasta templates configurada: {template_path}")
    
    # Inicialização do app Flask
    app = Flask(__name__, static_folder=static_path, template_folder=template_path)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    
    # Desabilitar debug e auto-reload em produção
    is_production = os.getenv('FLASK_ENV', 'production') == 'production'
    app.config['DEBUG'] = not is_production
    app.config['TESTING'] = False
    
    # Limite de tamanho de requisição
    app.config['MAX_CONTENT_LENGTH'] = config['request_max_mb'] * 1024 * 1024
    
    # Configurar CORS
    cors_origins = config['cors_allowed_origins']
    if cors_origins:
        CORS(app, origins=cors_origins)
        logger.info(f"✅ CORS configurado para: {cors_origins}")
    else:
        logger.warning("⚠️ CORS não configurado (nenhuma origem permitida)")
    
    # ProxyFix para headers corretos atrás de proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Configurar banco de dados
    from domain.interfaces.dataprovider.DatabaseConfig import init_database
    init_database(app, basedir)
    
    # Carregar base de conhecimento automaticamente se necessário
    with app.app_context():
        auto_load_knowledge_base()
    
    # Inicializar rate limiting
    from application.config.LimiterConfig import limiter
    limiter.init_app(app)
    
    # Middlewares de segurança e observabilidade
    app.before_request(add_request_id)
    app.before_request(log_request)
    app.after_request(add_security_headers)
    app.after_request(log_response)
    
    # Importar blueprints só depois das extensões serem inicializadas
    from adapter.entrypoint.etp.EtpController import etp_bp
    from adapter.entrypoint.etp.EtpDynamicController import etp_dynamic_bp
    from adapter.entrypoint.user.UserController import user_bp
    from adapter.entrypoint.chat.ChatController import chat_bp
    from adapter.entrypoint.health.HealthController import health_bp
    from adapter.entrypoint.admin.AdminController import admin_bp
    from adapter.entrypoint.kb.KbController import kb_blueprint
    
    # Registrar blueprints (rotas)
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/api')
    app.register_blueprint(etp_bp, url_prefix='/api/etp')
    app.register_blueprint(etp_dynamic_bp, url_prefix='/api/etp-dynamic')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(kb_blueprint)  # KB blueprint already has url_prefix='/api/kb' defined
    app.register_blueprint(admin_bp)  # Admin blueprint already has url_prefix='/administracao' defined
    
    # Endpoint de métricas (Prometheus)
    @app.route('/metrics')
    def metrics():
        """Endpoint de métricas Prometheus (protegido por token)."""
        # Autenticação via token
        auth_header = request.headers.get('Authorization', '')
        metrics_token = os.getenv('METRICS_TOKEN', '')
        
        # Extrair token do header (formato: "Bearer <token>")
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else auth_header
        
        # Validar token
        if metrics_token and token != metrics_token:
            return jsonify({"error": "unauthorized"}), 401
        
        # Retornar métricas Prometheus
        if PROMETHEUS_AVAILABLE:
            return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
        else:
            return jsonify({
                "error": "prometheus_client não instalado",
                "message": "Instale com: pip install prometheus-client"
            }), 503
    
    # Servir arquivos estáticos
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        
        if static_folder_path is None:
            return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return f"index.html not found. Static folder: {static_folder_path}", 404
    
    logger.info("✅ Aplicação Flask configurada com sucesso!")
    
    return app
