from pathlib import Path

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user

from app import db
from app.models.workflow import Workflow
from app.models.dashboard import Dashboard
from app.models.arquivo_importado import ArquivoImportado
from app.services.theme_service import get_theme_context
from app.services.workflow_import_service import (
    ImportacaoArquivoErro,
    process_workflow_upload,
)

workflow_bp = Blueprint('workflow', __name__)

ALLOWED_CHART_TYPES = {
    'bar', 'line', 'pie', 'doughnut', 'radar', 'area', 'scatter', 'heatmap', 'gauge', 'table'
}

ALLOWED_METRICS = {
    'valor_periodo_1',
    'valor_periodo_2',
    'diferenca_absoluta',
    'diferenca_percentual'
}


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

    charts = (
        Dashboard.query
        .filter_by(workflow_id=workflow.id)
        .order_by(Dashboard.created_at.desc())
        .all()
    )

    theme = get_theme_context()
    return render_template(
        'workflow_charts.html',
        workflow=workflow,
        theme=theme,
        arquivo_atual=arquivo_atual,
        processed_data=processed_data,
        charts=[chart.to_dict() for chart in charts]
    )


@workflow_bp.route('/dashboard/<workflow_nome>')
@login_required
def workflow_view(workflow_nome):
    """Exibe a pagina do workflow selecionado."""
    workflow = _get_workflow_for_user_by_name(workflow_nome)
    arquivo_atual, processed_data = _get_processed_data_for_workflow(workflow.id)

    theme = get_theme_context()
    return render_template(
        'workflow_view.html',
        workflow=workflow,
        theme=theme,
        arquivo_atual=arquivo_atual,
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


@workflow_bp.route('/api/workflows/<int:workflow_id>/graficos', methods=['GET'])
@login_required
def listar_graficos(workflow_id):
    workflow = Workflow.query.filter_by(
        id=workflow_id,
        usuario_id=current_user.id
    ).first_or_404()

    charts = (
        Dashboard.query
        .filter_by(workflow_id=workflow.id)
        .order_by(Dashboard.created_at.desc())
        .all()
    )

    return jsonify([chart.to_dict() for chart in charts])


@workflow_bp.route('/api/workflows/<int:workflow_id>/graficos', methods=['POST'])
@login_required
def criar_grafico(workflow_id):
    workflow = Workflow.query.filter_by(
        id=workflow_id,
        usuario_id=current_user.id
    ).first_or_404()

    dados_requisicao = request.get_json() or {}

    chart_type = (dados_requisicao.get('chart_type') or '').lower()
    metric = dados_requisicao.get('metric')
    metrics = dados_requisicao.get('metrics') or []
    indicators = dados_requisicao.get('indicators') or []
    colors = dados_requisicao.get('colors') or []
    nome = dados_requisicao.get('nome') or dados_requisicao.get('title')
    options = dados_requisicao.get('options') or {}

    if chart_type not in ALLOWED_CHART_TYPES:
        return jsonify({'error': 'Tipo de grafico invalido.'}), 400

    if isinstance(metrics, str):
        metrics = [metrics]
    metrics = [item.lower() for item in metrics if isinstance(item, str) and item.strip()]
    if not metrics:
        if metric:
            metrics = [metric.lower()]
        else:
            return jsonify({'error': 'Selecione ao menos uma metrica.'}), 400

    metric_set = []
    for item in metrics:
        if item not in ALLOWED_METRICS:
            return jsonify({'error': 'Metrica invalida.'}), 400
        if item not in metric_set:
            metric_set.append(item)
    metrics = metric_set
    primary_metric = metrics[0]

    if not indicators or not isinstance(indicators, list):
        return jsonify({'error': 'Selecione ao menos um indicador.'}), 400

    arquivo_atual, processed_data = _get_processed_data_for_workflow(workflow.id)
    if not processed_data or not processed_data.get('indicadores'):
        return jsonify({'error': 'Nao ha dados processados para gerar graficos.'}), 400

    indicador_map = {item.get('indicador'): item for item in processed_data.get('indicadores', [])}
    indicadores_invalidos = [indicador for indicador in indicators if indicador not in indicador_map]
    if indicadores_invalidos:
        return jsonify({'error': f"Indicadores invalidos: {', '.join(indicadores_invalidos)}"}), 400

    expected_color_count = len(metrics) if len(metrics) > 1 else len(indicators)
    colors = [color for color in colors if isinstance(color, str) and color.strip()]
    if colors and len(colors) != expected_color_count:
        return jsonify({'error': 'Quantidade de cores deve corresponder aos itens selecionados.'}), 400

    theme = get_theme_context()
    palette = theme.get('chart_palette', [])
    if not colors:
        generated = []
        for idx in range(expected_color_count):
            if palette:
                generated.append(palette[idx % len(palette)])
            else:
                generated.append('#%06x' % (0x3366CC + idx * 3211))
        colors = generated

    colors = [color.upper() for color in colors]

    if not nome:
        nome = f"{chart_type.title()} - {primary_metric.replace('_', ' ').title()}"

    if not isinstance(options, dict):
        options = {}
    options['metrics'] = metrics
    options['color_mode'] = 'metric' if len(metrics) > 1 else 'indicator'

    novo_grafico = Dashboard(
        workflow_id=workflow.id,
        nome=nome,
        chart_type=chart_type,
        metric=primary_metric,
        indicators=indicators,
        colors=colors,
        options=options
    )

    try:
        db.session.add(novo_grafico)
        db.session.commit()
    except Exception as err:
        current_app.logger.exception('Falha ao criar grafico', exc_info=err)
        db.session.rollback()
        return jsonify({'error': 'Erro ao salvar grafico.'}), 500

    return jsonify({
        'message': 'Grafico criado com sucesso.',
        'grafico': novo_grafico.to_dict()
    }), 201


@workflow_bp.route('/api/workflows/<int:workflow_id>/graficos/<int:grafico_id>', methods=['DELETE'])
@login_required
def excluir_grafico(workflow_id, grafico_id):
    workflow = Workflow.query.filter_by(
        id=workflow_id,
        usuario_id=current_user.id
    ).first_or_404()

    grafico = Dashboard.query.filter_by(
        id=grafico_id,
        workflow_id=workflow.id
    ).first_or_404()

    try:
        db.session.delete(grafico)
        db.session.commit()
    except Exception as err:
        current_app.logger.exception('Falha ao excluir grafico', exc_info=err)
        db.session.rollback()
        return jsonify({'error': 'Erro ao excluir grafico.'}), 500

    return jsonify({'message': 'Grafico excluido com sucesso.'})


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
        'arquivo': arquivo.to_dict()
    })
