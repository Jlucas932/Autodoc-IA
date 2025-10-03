import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Criar aplicação Flask
app = Flask(__name__)

# Importar utilitários de segurança
from utils.security import mask_key

# Verificar se a API key está configurada
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY or OPENAI_API_KEY == 'sua_api_key_aqui':
    logger.error("API Key da OpenAI não configurada!")
    logger.error("Para corrigir:")
    logger.error("1. Edite o arquivo '.env'")
    logger.error("2. Substitua 'sua_api_key_aqui' pela sua chave real")
    logger.error("3. Para obter uma API key: https://platform.openai.com/api-keys")
    sys.exit(1)

# Configurar Flask
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database/app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurar CORS
from flask_cors import CORS
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Configurar SQLAlchemy usando DatabaseConfig existente
from domain.interfaces.dataprovider.DatabaseConfig import db, init_database
from sqlalchemy import func
# Adicionar func ao contexto do db para compatibilidade
db.func = func

# Inicializar banco de dados
init_database(app)

# Importar e registrar blueprints após a criação do app
from adapter.entrypoint.etp.EtpController import etp_bp
from adapter.entrypoint.etp.EtpDynamicController import etp_dynamic_bp
from adapter.entrypoint.etp.ConversationalFlowController import conversational_flow_bp
from adapter.entrypoint.admin.AdminController import admin_bp
from adapter.entrypoint.chat.ChatController import chat_bp
from adapter.entrypoint.user.UserController import user_bp
from adapter.entrypoint.health.HealthController import health_bp

# Registrar blueprints com prefixo /api
app.register_blueprint(etp_bp, url_prefix='/api/etp')
app.register_blueprint(etp_dynamic_bp, url_prefix='/api/etp-dynamic')
app.register_blueprint(conversational_flow_bp)  # já tem url_prefix='/api/conversational'
app.register_blueprint(admin_bp)  # já tem url_prefix='/administracao'
app.register_blueprint(chat_bp, url_prefix='/api/chat')
app.register_blueprint(user_bp, url_prefix='/api/user')
app.register_blueprint(health_bp, url_prefix='/api')

# Tabelas são criadas automaticamente pelo init_database

if __name__ == "__main__":
    # Criar diretório de logs se não existir
    os.makedirs('logs', exist_ok=True)
    
    logger.info("API Key configurada com sucesso!")
    logger.info("Usando API Key: %s", mask_key(OPENAI_API_KEY))
    logger.info("Iniciando servidor ETP Sistema Padronizado...")
    logger.info("Acesse: http://localhost:5000")
    logger.info("Para parar o servidor: Ctrl+C")
    logger.info("Iniciado em: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # Inicializar sistema RAG
    with app.app_context():
        try:
            from pathlib import Path
            import openai
            from rag.retrieval import get_retrieval_instance
            
            # Verificar se existem índices FAISS
            # O caminho foi corrigido para um caminho absoluto dentro do contêiner, 
            # refletindo o mapeamento de volume do docker-compose.yml
            index_dir = Path("/app/rag/index/faiss")
            
            if index_dir.exists() and (index_dir / "etp_index.faiss").exists():
                logger.info("Carregando índices RAG...")
                
                # Configurar cliente OpenAI se disponível
                openai_client = None
                try:
                    openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
                except Exception as e:
                    logger.warning("Não foi possível configurar cliente OpenAI: %s", e)
                
                # Inicializar sistema de retrieval
                retrieval = get_retrieval_instance(openai_client=openai_client)
                
                if retrieval.build_indices():
                    logger.info("Sistema RAG inicializado com sucesso!")
                else:
                    logger.warning("Falha ao carregar índices RAG")
            else:
                logger.info("Índices RAG não encontrados.")
                logger.info("Para criar os índices, execute:")
                logger.info("python -m rag.ingest_etps --rebuild")
                
        except Exception as e:
            logger.warning("Erro ao inicializar sistema RAG: %s", e)
            logger.info("A aplicação continuará funcionando sem o sistema RAG.")

    # Executar servidor Flask para desenvolvimento local
    app.run(host="0.0.0.0", port=5000, debug=True)