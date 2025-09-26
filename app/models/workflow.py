from app import db
from datetime import datetime

class Workflow(db.Model):
    __tablename__ = 'workflows'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text)
    tipo = db.Column(db.Enum('comparativo', 'evolucao', name='workflow_tipo'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento com User
    usuario = db.relationship('User', backref=db.backref('workflows', lazy=True))
    
    # Constraint para nome único por usuário
    __table_args__ = (
        db.UniqueConstraint('nome', 'usuario_id', name='unique_workflow_per_user'),
    )
    
    def __repr__(self):
        return f'<Workflow {self.nome}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'tipo': self.tipo,
            'usuario_id': self.usuario_id,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None
        }
