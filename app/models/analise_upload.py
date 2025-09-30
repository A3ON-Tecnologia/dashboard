from datetime import datetime

from app import db


class AnaliseUpload(db.Model):
    __tablename__ = 'analise_uploads'

    id = db.Column(db.Integer, primary_key=True)
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
            'data_upload': self.data_upload.isoformat() if self.data_upload else None
        }
