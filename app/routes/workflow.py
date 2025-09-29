from pathlib import Path

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user

from app import db
from app.models.workflow import Workflow
from app.models.arquivo_importado import ArquivoImportado
from app.services.theme_service import get_theme_context
from app.services.workflow_import_service import (
    ImportacaoArquivoErro,
    process_workflow_upload,
)

workflow_bp = Blueprint('workflow', __name__)


@workflow_bp.route('/dashboard')
@login_required
def dashboard():
    """Lista todos os workflows do usuario logado."""
    workflows = (
        Workflow.query
        .filter_by(usuario_id=current_user.id)
        .order_by(Workflow.data_criacao.desc())
        .all()
    )

    theme = get_theme_context()
    return render_template('dashboard.html', workflows=workflows, theme=theme)


@workflow_bp.route('/dashboard/<workflow_nome>')
@login_required
def workflow_view(workflow_nome):
    """Exibe a pagina do workflow selecionado."""
    workflow = Workflow.query.filter_by(
        nome=workflow_nome,
        usuario_id=current_user.id
    ).first_or_404()

    arquivo_atual = (
        ArquivoImportado.query
        .filter_by(workflow_id=workflow.id)
        .order_by(ArquivoImportado.data_upload.desc())
        .first()
    )

    theme = get_theme_context()
    return render_template(
        'workflow_view.html',
        workflow=workflow,
        theme=theme,
        arquivo_atual=arquivo_atual,
        processed_data=arquivo_atual.dados_extraidos if arquivo_atual else None
    )


@workflow_bp.route('/api/workflows', methods=['GET'])
@login_required
def get_workflows():
    """API para listar workflows do usuario."""
    workflows = (
        Workflow.query
        .filter_by(usuario_id=current_user.id)
        .order_by(Workflow.data_criacao.desc())
        .all()
    )
    return jsonify([workflow.to_dict() for workflow in workflows])


@workflow_bp.route('/api/workflows', methods=['POST'])
@login_required
def create_workflow():
    """API para criar novo workflow."""
    data = request.get_json()

    if not data or not data.get('nome') or not data.get('tipo'):
        return jsonify({'error': 'Nome e tipo sao obrigatorios.'}), 400

    existing = Workflow.query.filter_by(
        nome=data['nome'],
        usuario_id=current_user.id
    ).first()

    if existing:
        return jsonify({'error': 'Ja existe um workflow com este nome.'}), 400

    if data['tipo'] not in ['comparativo', 'evolucao']:
        return jsonify({'error': 'Tipo deve ser "comparativo" ou "evolucao".'}), 400

    try:
        workflow = Workflow(
            nome=data['nome'],
            descricao=data.get('descricao', ''),
            tipo=data['tipo'],
            usuario_id=current_user.id
        )
        db.session.add(workflow)
        db.session.commit()
        return jsonify({
            'message': 'Workflow criado com sucesso!',
            'workflow': workflow.to_dict()
        }), 201
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro ao criar workflow.'}), 500


@workflow_bp.route('/api/workflows/<int:workflow_id>', methods=['PUT'])
@login_required
def update_workflow(workflow_id):
    """API para atualizar workflow."""
    workflow = Workflow.query.filter_by(
        id=workflow_id,
        usuario_id=current_user.id
    ).first_or_404()

    data = request.get_json()

    if not data:
        return jsonify({'error': 'Dados nao fornecidos.'}), 400

    if 'nome' in data and data['nome'] != workflow.nome:
        existing = Workflow.query.filter_by(
            nome=data['nome'],
            usuario_id=current_user.id
        ).first()
        if existing:
            return jsonify({'error': 'Ja existe um workflow com este nome.'}), 400

    if 'tipo' in data and data['tipo'] not in ['comparativo', 'evolucao']:
        return jsonify({'error': 'Tipo deve ser "comparativo" ou "evolucao".'}), 400

    try:
        if 'nome' in data:
            workflow.nome = data['nome']
        if 'descricao' in data:
            workflow.descricao = data['descricao']
        if 'tipo' in data:
            workflow.tipo = data['tipo']

        db.session.commit()
        return jsonify({
            'message': 'Workflow atualizado com sucesso!',
            'workflow': workflow.to_dict()
        })
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro ao atualizar workflow.'}), 500


@workflow_bp.route('/api/workflows/<int:workflow_id>', methods=['DELETE'])
@login_required
def delete_workflow(workflow_id):
    """API para excluir workflow."""
    workflow = Workflow.query.filter_by(
        id=workflow_id,
        usuario_id=current_user.id
    ).first_or_404()

    try:
        db.session.delete(workflow)
        db.session.commit()
        return jsonify({'message': 'Workflow excluido com sucesso!'})
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro ao excluir workflow.'}), 500


@workflow_bp.route('/api/workflows/<int:workflow_id>/arquivos', methods=['POST'])
@login_required
def upload_arquivo(workflow_id):
    workflow = Workflow.query.filter_by(
        id=workflow_id,
        usuario_id=current_user.id
    ).first_or_404()

    if 'arquivo' not in request.files:
        return jsonify({'error': 'Nenhum arquivo encontrado no upload.'}), 400

    arquivo = request.files['arquivo']
    upload_root = Path(current_app.config['UPLOAD_FOLDER']) / f'workflow_{workflow.id}'

    try:
        resultado = process_workflow_upload(arquivo, workflow.id, upload_root)
    except ImportacaoArquivoErro as exc:
        return jsonify({'error': str(exc)}), 400

    novo_arquivo = ArquivoImportado(
        workflow_id=workflow.id,
        nome_arquivo=resultado['nome_arquivo'],
        caminho_arquivo=str(resultado['arquivo_salvo']),
        dados_extraidos=resultado['payload']
    )

    try:
        db.session.add(novo_arquivo)
        db.session.commit()
    except Exception:
        db.session.rollback()
        destino = resultado['arquivo_salvo']
        if isinstance(destino, Path):
            try:
                destino.unlink()
            except FileNotFoundError:
                pass
        return jsonify({'error': 'Falha ao salvar os dados processados.'}), 500

    return jsonify({
        'message': 'Arquivo valido processado com sucesso.',
        'arquivo': novo_arquivo.to_dict(),
        'dados_processados': novo_arquivo.dados_extraidos
    }), 201


@workflow_bp.route('/api/workflows/<int:workflow_id>/arquivos', methods=['GET'])
@login_required
def listar_arquivos(workflow_id):
    workflow = Workflow.query.filter_by(
        id=workflow_id,
        usuario_id=current_user.id
    ).first_or_404()

    arquivos = (
        ArquivoImportado.query
        .filter_by(workflow_id=workflow.id)
        .order_by(ArquivoImportado.data_upload.desc())
        .all()
    )

    return jsonify([arquivo.to_dict() for arquivo in arquivos])


@workflow_bp.route('/api/workflows/<int:workflow_id>/comparativo', methods=['GET'])
@login_required
def obter_dados_comparativo(workflow_id):
    workflow = Workflow.query.filter_by(
        id=workflow_id,
        usuario_id=current_user.id
    ).first_or_404()

    arquivo = (
        ArquivoImportado.query
        .filter_by(workflow_id=workflow.id)
        .order_by(ArquivoImportado.data_upload.desc())
        .first()
    )

    if not arquivo or not arquivo.dados_extraidos:
        return jsonify({'dados': None, 'arquivo': None})

    return jsonify({
        'dados': arquivo.dados_extraidos,
        'arquivo': arquivo.to_dict()
    })