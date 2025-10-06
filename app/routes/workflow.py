from pathlib import Path
from typing import Any, Dict

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
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

WORKFLOW_ALLOWED_TYPES = {'balancete', 'analise_jp'}


def _serialize_arquivo_metadata(
    arquivo: ArquivoImportado,
    include_counts: bool = False,
) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {
        'id': arquivo.id,
        'workflow_id': arquivo.workflow_id,
        'nome_arquivo': arquivo.nome_arquivo,
        'data_upload': arquivo.data_upload.isoformat() if arquivo.data_upload else None,
    }

    if include_counts:
        total_indicadores = 0

        dados_extraidos = arquivo.dados_extraidos or {}

        dados_extraidos = arquivo.dados_extraidos

        if isinstance(dados_extraidos, dict):
            raw_total = dados_extraidos.get('total_indicadores')
            if isinstance(raw_total, (int, float)):
                total_indicadores = int(raw_total)
            else:
                indicadores = dados_extraidos.get('indicadores')
                if isinstance(indicadores, list):
                    total_indicadores = len(indicadores)

        metadata['total_indicadores'] = total_indicadores

    return metadata
  
def _get_workflow_for_user_by_name(workflow_nome):
    return Workflow.query.filter_by(
        nome=workflow_nome,
        usuario_id=current_user.id
    ).first_or_404()


def _get_latest_file_for_workflow(workflow_id):
    return (
        ArquivoImportado.query
        .filter_by(workflow_id=workflow_id)
        .order_by(ArquivoImportado.data_upload.desc())
        .first()
    )


def _get_processed_data_for_workflow(workflow_id):
    arquivo = _get_latest_file_for_workflow(workflow_id)
    return arquivo, arquivo.dados_extraidos if arquivo else None




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


@workflow_bp.route('/dashboard/<workflow_nome>/graficos')
@login_required
def workflow_charts_view(workflow_nome):
    workflow = _get_workflow_for_user_by_name(workflow_nome)
    arquivo_atual, processed_data = _get_processed_data_for_workflow(workflow.id)

    theme = get_theme_context()
    return render_template(
        'workflow_charts.html',
        workflow=workflow,
        theme=theme,
        arquivo_atual=arquivo_atual,
        processed_data=processed_data,
    )


@workflow_bp.route('/dashboard/<workflow_nome>')
@login_required
def workflow_view(workflow_nome):
    """Exibe a pagina do workflow selecionado."""
    workflow = _get_workflow_for_user_by_name(workflow_nome)
    if workflow.tipo == 'analise_jp':
        return redirect(url_for('analise_jp.analise_jp_view', workflow_id=workflow.id))

    arquivo_atual, processed_data = _get_processed_data_for_workflow(workflow.id)
    arquivo_atual_metadata = (
        _serialize_arquivo_metadata(arquivo_atual)
        if arquivo_atual
        else None
    )

    theme = get_theme_context()
    return render_template(
        'workflow_view.html',
        workflow=workflow,
        theme=theme,
        arquivo_atual=arquivo_atual,
        arquivo_atual_metadata=arquivo_atual_metadata,
        processed_data=processed_data
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

    if data['tipo'] not in WORKFLOW_ALLOWED_TYPES:
        return jsonify({'error': 'Tipo deve ser "balancete" ou "analise_jp".'}), 400

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

    if 'tipo' in data and data['tipo'] not in WORKFLOW_ALLOWED_TYPES:
        return jsonify({'error': 'Tipo deve ser "balancete" ou "analise_jp".'}), 400

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
        'arquivo': _serialize_arquivo_metadata(novo_arquivo),
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

    return jsonify([
        _serialize_arquivo_metadata(arquivo, include_counts=True)
        for arquivo in arquivos
    ])

    return jsonify([arquivo.to_dict() for arquivo in arquivos])





@workflow_bp.route('/api/workflows/<int:workflow_id>/arquivos/<int:arquivo_id>', methods=['DELETE'])
@login_required
def excluir_arquivo(workflow_id, arquivo_id):
    workflow = Workflow.query.filter_by(
        id=workflow_id,
        usuario_id=current_user.id
    ).first_or_404()

    arquivo = ArquivoImportado.query.filter_by(
        id=arquivo_id,
        workflow_id=workflow.id
    ).first_or_404()

    caminho_arquivo = Path(arquivo.caminho_arquivo) if arquivo.caminho_arquivo else None

    try:
        db.session.delete(arquivo)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro ao excluir arquivo.'}), 500

    if caminho_arquivo and caminho_arquivo.exists():
        try:
            caminho_arquivo.unlink()
        except OSError:
            current_app.logger.warning('Nao foi possivel remover o arquivo fisico %s', caminho_arquivo)

    return jsonify({'message': 'Arquivo excluido com sucesso.'})


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
        'arquivo': _serialize_arquivo_metadata(arquivo)
    })
