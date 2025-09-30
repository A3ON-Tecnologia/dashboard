from datetime import datetime
from pathlib import Path


from app import db


class AnaliseUpload(db.Model):
    __tablename__ = 'analise_uploads'

    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=False)
    categoria = db.Column(db.String(120), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    caminho_arquivo = db.Column(db.String(500), nullable=False)
    dados_extraidos = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    workflow = db.relationship(
        'Workflow',
        backref=db.backref('analise_uploads', lazy='dynamic', cascade='all, delete-orphan')
    )

    def to_dict(self):
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=False, index=True)
    categoria = db.Column(db.String(64), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    caminho_arquivo = db.Column(db.String(512), nullable=False)
    dados_extraidos = db.Column(db.JSON, nullable=False)
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_analise_uploads_workflow_categoria', 'workflow_id', 'categoria'),
    )

    def __repr__(self) -> str:
        return f"<AnaliseUpload {self.categoria} ({self.nome_arquivo})>"

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'categoria': self.categoria,
            'nome_arquivo': self.nome_arquivo,
            'caminho_arquivo': self.caminho_arquivo,
            'dados_extraidos': self.dados_extraidos,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @staticmethod
    def build_storage_path(base_path: Path, workflow_id: int, categoria: str, filename: str) -> Path:
        return base_path / 'analise_jp' / str(workflow_id) / categoria / filename
            'data_upload': self.data_upload.isoformat() if self.data_upload else None
        }
