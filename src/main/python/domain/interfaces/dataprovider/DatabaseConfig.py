"""
Configuração de banco de dados multi-SGBD com pool_pre_ping e URL.create.
Suporta PostgreSQL, MySQL/MariaDB, SQL Server (pyodbc) e SQLite.
"""
import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, MetaData
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.pool import NullPool

# Configurar logging
logger = logging.getLogger(__name__)

# Naming convention para Alembic (portável entre SGBDs)
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# Metadata com naming convention
metadata = MetaData(naming_convention=naming_convention)

# Base declarativa
Base = declarative_base(metadata=metadata)


def mask_db_url(url: str) -> str:
    """
    Mascara credenciais na URL do banco para logging seguro.
    
    Args:
        url: URL do banco de dados
    
    Returns:
        URL mascarada
    """
    if not url or '://' not in url:
        return "****"
    
    try:
        # Formato: dialect://user:password@host:port/database
        parts = url.split('://')
        dialect = parts[0]
        
        if '@' in parts[1]:
            credentials, rest = parts[1].split('@', 1)
            if ':' in credentials:
                user = credentials.split(':')[0]
                masked_credentials = f"{user}:****"
            else:
                masked_credentials = "****"
            
            return f"{dialect}://{masked_credentials}@{rest}"
        else:
            # SQLite ou sem credenciais
            return url
    except Exception:
        return "****"


def _make_engine():
    """
    Cria engine SQLAlchemy com configuração multi-SGBD.
    
    Returns:
        Engine configurada
    """
    db_url = os.getenv("DATABASE_URL", "sqlite:///./local.db")
    
    # Parâmetros de pool configuráveis
    pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    
    # Detectar dialeto
    dialect = db_url.split('://')[0].split('+')[0] if '://' in db_url else 'sqlite'
    
    # Log mascarado
    masked_url = mask_db_url(db_url)
    logger.info(f"🔗 Conectando ao banco: {masked_url} (dialeto: {dialect})")
    
    # Configurações específicas por dialeto
    engine_kwargs = {
        'pool_pre_ping': True,  # OBRIGATÓRIO: detecta conexões quebradas
        'future': True,
    }
    
    # SQLite não usa pooling
    if dialect == 'sqlite':
        engine_kwargs['poolclass'] = NullPool
        logger.info("SQLite detectado: pooling desabilitado")
    else:
        engine_kwargs.update({
            'pool_size': pool_size,
            'max_overflow': max_overflow,
            'pool_recycle': pool_recycle,
        })
        logger.info(f"Pool configurado: size={pool_size}, overflow={max_overflow}, recycle={pool_recycle}s")
    
    # Criar engine
    engine = create_engine(db_url, **engine_kwargs)
    
    return engine


# Engine global
_engine = None

def get_engine():
    """Retorna engine singleton."""
    global _engine
    if _engine is None:
        _engine = _make_engine()
    return _engine


# SessionLocal factory
SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False, future=True)


class DBConnectionHandler:
    """
    Context manager para gerenciar conexões e sessões do banco.
    
    Uso:
        # Transacional (com commit/rollback)
        with DBConnectionHandler() as session:
            session.add(obj)
        
        # Read-only (sem transação)
        with DBConnectionHandler(read_only=True) as conn:
            result = conn.execute(query)
    """
    
    def __init__(self, read_only=False):
        """
        Inicializa handler.
        
        Args:
            read_only: Se True, usa conexão read-only sem transação
        """
        self.read_only = read_only
        self.session = None
        self.connection = None
    
    def __enter__(self):
        """Abre sessão ou conexão."""
        if self.read_only:
            self.connection = get_engine().connect()
            return self.connection
        else:
            self.session = SessionLocal()
            return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Fecha sessão ou conexão com commit/rollback apropriado."""
        if self.read_only:
            if self.connection:
                self.connection.close()
        else:
            try:
                if exc_type is None:
                    self.session.commit()
                else:
                    self.session.rollback()
                    logger.error(f"Transação revertida devido a erro: {exc_val}")
            finally:
                self.session.close()


@contextmanager
def transactional():
    """
    Context manager para operações transacionais.
    
    Uso:
        with transactional() as session:
            session.add(obj)
    """
    with DBConnectionHandler(read_only=False) as session:
        yield session


@contextmanager
def read_only():
    """
    Context manager para operações read-only.
    
    Uso:
        with read_only() as conn:
            result = conn.execute(query)
    """
    with DBConnectionHandler(read_only=True) as conn:
        yield conn


def get_db_session():
    """
    Retorna uma nova sessão do banco.
    Útil para uso direto fora de context managers.
    
    ATENÇÃO: O chamador é responsável por fechar a sessão.
    
    Returns:
        Session
    """
    return SessionLocal()


# Flask-SQLAlchemy compatibility layer
class _FlaskSQLAlchemyCompat:
    """Camada de compatibilidade para código que usa Flask-SQLAlchemy."""
    
    def __init__(self):
        from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
        from sqlalchemy.orm import relationship
        
        self.Model = Base
        self.session = scoped_session(SessionLocal)
        self.metadata = metadata
        
        # Expor tipos SQLAlchemy para compatibilidade
        self.Column = Column
        self.Integer = Integer
        self.String = String
        self.Text = Text
        self.DateTime = DateTime
        self.Float = Float
        self.Boolean = Boolean
        self.ForeignKey = ForeignKey
        self.relationship = relationship
    
    def init_app(self, app):
        """Inicializa com app Flask."""
        # Criar tabelas se não existirem
        with app.app_context():
            metadata.create_all(bind=get_engine())
            logger.info("✅ Tabelas do banco criadas/verificadas")
    
    def create_all(self):
        """Cria todas as tabelas."""
        metadata.create_all(bind=get_engine())
    
    def drop_all(self):
        """Remove todas as tabelas."""
        metadata.drop_all(bind=get_engine())


# Instância global para compatibilidade
db = _FlaskSQLAlchemyCompat()


def init_database(app, basedir=None):
    """
    Inicializa banco de dados com app Flask.
    
    Args:
        app: Instância Flask
        basedir: Diretório base (não usado, mantido para compatibilidade)
    """
    db.init_app(app)
    logger.info("✅ Banco de dados inicializado com sucesso")
