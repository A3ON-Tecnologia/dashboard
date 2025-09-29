from datetime import datetime
from app import db


class ArquivoImportado(db.Model):
    __tablename__ = 'arquivos_importados'

    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=False, index=True)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    caminho_arquivo = db.Column(db.String(512), nullable=False)
    dados_extraidos = db.Column(db.JSON, nullable=True)
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)

    workflow = db.relationship('Workflow', backref=db.backref('arquivos_importados', lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<ArquivoImportado {self.nome_arquivo} (workflow={self.workflow_id})>"

    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'nome_arquivo': self.nome_arquivo,
            'caminho_arquivo': self.caminho_arquivo,
            'dados_extraidos': self.dados_extraidos,
            'data_upload': self.data_upload.isoformat() if self.data_upload else None
        }