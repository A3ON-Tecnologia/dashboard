from datetime import datetime

from app import db


class Dashboard(db.Model):
    __tablename__ = 'dashboards'

    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflows.id'), nullable=False, index=True)
    nome = db.Column(db.String(120), nullable=True)
    chart_type = db.Column(db.String(50), nullable=False)
    metric = db.Column(db.String(50), nullable=False)
    indicators = db.Column(db.JSON, nullable=False)
    colors = db.Column(db.JSON, nullable=False)
    options = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workflow = db.relationship('Workflow', backref=db.backref('dashboards', lazy='dynamic', cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<Dashboard {self.chart_type} (workflow={self.workflow_id})>"

    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'nome': self.nome,
            'chart_type': self.chart_type,
            'metric': self.metric,
            'indicators': self.indicators or [],
            'colors': self.colors or [],
            'options': self.options or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
