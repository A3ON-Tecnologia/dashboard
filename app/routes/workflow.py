from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.workflow import Workflow
from app.services.theme_service import get_theme_context

workflow_bp = Blueprint('workflow', __name__)

@workflow_bp.route('/dashboard')
@login_required
def dashboard():
    """Lista todos os workflows do usuário logado"""
    print(f"DEBUG: Usuario atual ID: {current_user.id}")
    print(f"DEBUG: Consultando workflows para usuario_id: {current_user.id}")
    workflows = Workflow.query.filter_by(usuario_id=current_user.id).order_by(Workflow.data_criacao.desc()).all()
    print(f"DEBUG: Workflows encontrados para o usuário atual: {len(workflows)}")
    
    # Verificar todos os workflows na tabela para depuração
    all_workflows = Workflow.query.all()
    print(f"DEBUG: Total de workflows na tabela: {len(all_workflows)}")
    for w in all_workflows:
        print(f"DEBUG: Workflow na tabela - ID: {w.id}, Nome: {w.nome}, Usuario ID: {w.usuario_id}")
    
    theme = get_theme_context()
    return render_template('dashboard.html', workflows=workflows, theme=theme)

@workflow_bp.route('/dashboard/<workflow_nome>')
@login_required
def workflow_view(workflow_nome):
    """Visualização individual de um workflow"""
    workflow = Workflow.query.filter_by(
        nome=workflow_nome, 
        usuario_id=current_user.id
    ).first_or_404()
    print(f"DEBUG: Workflow sendo visualizado: {workflow.nome}")
    theme = get_theme_context()
    return render_template('workflow_view.html', workflow=workflow, theme=theme)

@workflow_bp.route('/api/workflows', methods=['GET'])
@login_required
def get_workflows():
    """API para listar workflows do usuário"""
    workflows = Workflow.query.filter_by(usuario_id=current_user.id).order_by(Workflow.data_criacao.desc()).all()
    print(f"DEBUG: Workflows sendo retornados pela API: {[w.nome for w in workflows]}")
    return jsonify([workflow.to_dict() for workflow in workflows])

@workflow_bp.route('/api/workflows', methods=['POST'])
@login_required
def create_workflow():
    """API para criar novo workflow"""
    data = request.get_json()
    
    if not data or not data.get('nome') or not data.get('tipo'):
        return jsonify({'error': 'Nome e tipo são obrigatórios'}), 400
    
    # Verificar se já existe workflow com mesmo nome para o usuário
    existing = Workflow.query.filter_by(
        nome=data['nome'], 
        usuario_id=current_user.id
    ).first()
    
    if existing:
        return jsonify({'error': 'Já existe um workflow com este nome'}), 400
    
    # Validar tipo
    if data['tipo'] not in ['comparativo', 'evolucao']:
        return jsonify({'error': 'Tipo deve ser "comparativo" ou "evolucao"'}), 400
    
    try:
        workflow = Workflow(
            nome=data['nome'],
            descricao=data.get('descricao', ''),
            tipo=data['tipo'],
            usuario_id=current_user.id
        )
        
        db.session.add(workflow)
        db.session.commit()
        
        print(f"DEBUG: Workflow criado: {workflow.nome}")
        return jsonify({
            'message': 'Workflow criado com sucesso!',
            'workflow': workflow.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao criar workflow'}), 500

@workflow_bp.route('/api/workflows/<int:workflow_id>', methods=['PUT'])
@login_required
def update_workflow(workflow_id):
    """API para atualizar workflow"""
    workflow = Workflow.query.filter_by(
        id=workflow_id, 
        usuario_id=current_user.id
    ).first_or_404()
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Dados não fornecidos'}), 400
    
    # Verificar se novo nome já existe (se foi alterado)
    if 'nome' in data and data['nome'] != workflow.nome:
        existing = Workflow.query.filter_by(
            nome=data['nome'], 
            usuario_id=current_user.id
        ).first()
        
        if existing:
            return jsonify({'error': 'Já existe um workflow com este nome'}), 400
    
    # Validar tipo se fornecido
    if 'tipo' in data and data['tipo'] not in ['comparativo', 'evolucao']:
        return jsonify({'error': 'Tipo deve ser "comparativo" ou "evolucao"'}), 400
    
    try:
        # Atualizar campos
        if 'nome' in data:
            workflow.nome = data['nome']
        if 'descricao' in data:
            workflow.descricao = data['descricao']
        if 'tipo' in data:
            workflow.tipo = data['tipo']
        
        db.session.commit()
        
        print(f"DEBUG: Workflow atualizado: {workflow.nome}")
        return jsonify({
            'message': 'Workflow atualizado com sucesso!',
            'workflow': workflow.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao atualizar workflow'}), 500

@workflow_bp.route('/api/workflows/<int:workflow_id>', methods=['DELETE'])
@login_required
def delete_workflow(workflow_id):
    """API para excluir workflow"""
    workflow = Workflow.query.filter_by(
        id=workflow_id, 
        usuario_id=current_user.id
    ).first_or_404()
    
    try:
        db.session.delete(workflow)
        db.session.commit()
        
        print(f"DEBUG: Workflow excluído: {workflow.nome}")
        return jsonify({'message': 'Workflow excluído com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Erro ao excluir workflow'}), 500


