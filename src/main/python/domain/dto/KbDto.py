"""
Modelos de dados para a base de conhecimento (Knowledge Base).
Tipos portáveis para suporte multi-SGBD (PostgreSQL, MySQL, SQL Server, SQLite).
Embeddings armazenados apenas no FAISS (filesystem), não no banco.
"""
from domain.interfaces.dataprovider.DatabaseConfig import db
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class KbDocument(db.Model):
    """
    Modelo para documentos da base de conhecimento.
    Armazena metadados de documentos ETP ingeridos.
    """
    __tablename__ = 'kb_document'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    etp_id = db.Column(db.Integer, db.ForeignKey('etp_sessions.id'), nullable=True)
    objective_slug = db.Column(db.String(100), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    chunks = db.relationship('KbChunk', backref='kb_document', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<KbDocument {self.filename}>'
    
    def to_dict(self):
        """Converte o modelo para dicionário."""
        return {
            'id': self.id,
            'filename': self.filename,
            'etp_id': self.etp_id,
            'objective_slug': self.objective_slug,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'chunks_count': len(self.chunks) if self.chunks else 0
        }


class KbChunk(db.Model):
    """
    Modelo para chunks (fragmentos) da base de conhecimento.
    Armazena texto e metadados. Embeddings ficam no FAISS (filesystem).
    """
    __tablename__ = 'kb_chunk'
    
    id = db.Column(db.Integer, primary_key=True)
    kb_document_id = db.Column(db.Integer, db.ForeignKey('kb_document.id'), nullable=False, index=True)
    section_type = db.Column(db.String(50), nullable=False, index=True)
    content_text = db.Column(db.Text, nullable=False)
    objective_slug = db.Column(db.String(100), nullable=False, index=True)
    
    # Citações armazenadas como JSON serializado (portável)
    citations_json = db.Column(db.Text, nullable=True)
    
    # Metadados adicionais (portável)
    metadata_json = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # NOTA: Embeddings NÃO são armazenados no banco.
    # Eles ficam no FAISS (filesystem) e são referenciados pelo ID do chunk.

    def __repr__(self):
        return f'<KbChunk {self.id} - {self.section_type}>'

    @property
    def content(self):
        """Propriedade para compatibilidade - mapeia para content_text."""
        return self.content_text
    
    @content.setter
    def content(self, value):
        """Setter para compatibilidade - mapeia para content_text."""
        self.content_text = value
    
    def get_citations(self):
        """
        Retorna as citações como dicionário.
        
        Returns:
            dict: Citações deserializadas ou {} se vazio
        """
        if self.citations_json:
            try:
                return json.loads(self.citations_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Erro ao deserializar citations_json do chunk {self.id}: {e}")
                return {}
        return {}
    
    def set_citations(self, citations_dict):
        """
        Define as citações a partir de um dicionário.
        
        Args:
            citations_dict: Dicionário com citações
        """
        if citations_dict:
            self.citations_json = json.dumps(citations_dict, ensure_ascii=False)
        else:
            self.citations_json = None
    
    def get_metadata(self):
        """
        Retorna os metadados como dicionário.
        
        Returns:
            dict: Metadados deserializados ou {} se vazio
        """
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Erro ao deserializar metadata_json do chunk {self.id}: {e}")
                return {}
        return {}
    
    def set_metadata(self, metadata_dict):
        """
        Define os metadados a partir de um dicionário.
        
        Args:
            metadata_dict: Dicionário com metadados
        """
        if metadata_dict:
            self.metadata_json = json.dumps(metadata_dict, ensure_ascii=False)
        else:
            self.metadata_json = None
    
    def to_dict(self):
        """Converte o modelo para dicionário."""
        return {
            'id': self.id,
            'kb_document_id': self.kb_document_id,
            'section_type': self.section_type,
            'content_text': self.content_text,
            'objective_slug': self.objective_slug,
            'citations': self.get_citations(),
            'metadata': self.get_metadata(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def content_preview(self, max_chars=200):
        """
        Retorna uma prévia do conteúdo do chunk.
        
        Args:
            max_chars: Número máximo de caracteres
        
        Returns:
            str: Prévia do conteúdo
        """
        if len(self.content_text) <= max_chars:
            return self.content_text
        return self.content_text[:max_chars] + "..."


class LegalNormCache(db.Model):
    """
    Modelo para cache de normas legais (LexML).
    Armazena dados de normas consultadas para evitar requisições repetidas.
    """
    __tablename__ = 'legal_norm_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    norm_urn = db.Column(db.String(500), nullable=False, unique=True, index=True)
    norm_label = db.Column(db.String(1000), nullable=False)
    sphere = db.Column(db.String(50), nullable=False, index=True)  # federal, estadual, municipal
    status = db.Column(db.String(50), nullable=False, index=True)  # active, revoked, modified
    
    # Dados da fonte armazenados como JSON serializado (portável)
    source_json = db.Column(db.Text, nullable=True)
    
    last_verified_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<LegalNormCache {self.norm_urn}>'
    
    def get_source_data(self):
        """
        Retorna os dados da fonte como dicionário.
        
        Returns:
            dict: Dados da fonte deserializados ou {} se vazio
        """
        if self.source_json:
            try:
                return json.loads(self.source_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Erro ao deserializar source_json da norma {self.norm_urn}: {e}")
                return {}
        return {}
    
    def set_source_data(self, source_dict):
        """
        Define os dados da fonte a partir de um dicionário.
        
        Args:
            source_dict: Dicionário com dados da fonte
        """
        if source_dict:
            self.source_json = json.dumps(source_dict, ensure_ascii=False)
        else:
            self.source_json = None
    
    def to_dict(self):
        """Converte o modelo para dicionário."""
        return {
            'id': self.id,
            'norm_urn': self.norm_urn,
            'norm_label': self.norm_label,
            'sphere': self.sphere,
            'status': self.status,
            'source_data': self.get_source_data(),
            'last_verified_at': self.last_verified_at.isoformat() if self.last_verified_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def is_recent(self, days=None):
        """
        Verifica se a norma foi verificada recentemente.
        
        Args:
            days: Número de dias para considerar recente (padrão: LEGAL_CACHE_TTL_DAYS)
        
        Returns:
            bool: True se a norma foi verificada recentemente
        """
        if not self.last_verified_at:
            return False
        
        import os
        from datetime import timedelta
        
        if days is None:
            days = int(os.getenv('LEGAL_CACHE_TTL_DAYS', '7'))
        
        return (datetime.utcnow() - self.last_verified_at) <= timedelta(days=days)
