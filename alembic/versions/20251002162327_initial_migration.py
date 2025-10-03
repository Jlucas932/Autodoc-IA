"""Initial migration

Revision ID: 20251002162327
Revises: 
Create Date: 2025-10-02T16:23:27.498002

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251002162327'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial tables."""
    # kb_documents
    op.create_table(
        'kb_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('source_type', sa.String(length=50), nullable=True),
        sa.Column('source_path', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_kb_documents')),
        sa.UniqueConstraint('document_id', name=op.f('uq_kb_documents_document_id'))
    )
    op.create_index(op.f('ix_document_id'), 'kb_documents', ['document_id'], unique=False)
    
    # kb_chunks
    op.create_table(
        'kb_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chunk_id', sa.String(length=255), nullable=False),
        sa.Column('document_id', sa.String(length=255), nullable=False),
        sa.Column('section_type', sa.String(length=100), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('citations_json', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_kb_chunks')),
        sa.UniqueConstraint('chunk_id', name=op.f('uq_kb_chunks_chunk_id')),
        sa.ForeignKeyConstraint(['document_id'], ['kb_documents.document_id'], name=op.f('fk_kb_chunks_document_id_kb_documents'))
    )
    op.create_index(op.f('ix_chunk_id'), 'kb_chunks', ['chunk_id'], unique=False)
    op.create_index(op.f('ix_section_type'), 'kb_chunks', ['section_type'], unique=False)
    
    # etp_sessions
    op.create_table(
        'etp_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('necessity', sa.Text(), nullable=True),
        sa.Column('requirements_json', sa.Text(), nullable=True),
        sa.Column('procurement_path', sa.String(length=50), nullable=True),
        sa.Column('conversation_stage', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_etp_sessions')),
        sa.UniqueConstraint('session_id', name=op.f('uq_etp_sessions_session_id'))
    )
    op.create_index(op.f('ix_session_id'), 'etp_sessions', ['session_id'], unique=False)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index(op.f('ix_session_id'), table_name='etp_sessions')
    op.drop_table('etp_sessions')
    op.drop_index(op.f('ix_section_type'), table_name='kb_chunks')
    op.drop_index(op.f('ix_chunk_id'), table_name='kb_chunks')
    op.drop_table('kb_chunks')
    op.drop_index(op.f('ix_document_id'), table_name='kb_documents')
    op.drop_table('kb_documents')
