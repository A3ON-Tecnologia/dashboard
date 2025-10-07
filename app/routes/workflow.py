from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
)
from flask_login import login_required, current_user
from sqlalchemy.orm import defer

from app import db
from app.models.workflow import Workflow
from app.models.arquivo_importado import ArquivoImportado
from app.models.dashboard import Dashboard
from app.models.analise_jp_chart import AnaliseJPChart
from app.services.theme_service import get_theme_context
from app.services.workflow_import_service import (
    ImportacaoArquivoErro,
    process_workflow_upload,
)
from app.routes.analise_jp import (
    build_analise_jp_dashboard_context,
    build_analise_jp_charts_context,
    _slug_to_label,
    _validate_category,
)

workflow_bp = Blueprint('workflow', __name__)

WORKFLOW_ALLOWED_TYPES = {'balancete', 'analise_jp'}
ALLOWED_CHART_TYPES = {'bar', 'bar-horizontal', 'line', 'area', 'pie'}


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


def _get_workflow_for_user(workflow_id: int) -> Workflow:
    return Workflow.query.filter_by(
        id=workflow_id,
        usuario_id=current_user.id
    ).first_or_404()


def _get_latest_file_for_workflow(workflow_id, include_payload: bool = True):
    query = (
        ArquivoImportado.query
        .filter_by(workflow_id=workflow_id)
        .order_by(ArquivoImportado.data_upload.desc())
    )

    if not include_payload:
        query = query.options(defer(ArquivoImportado.dados_extraidos))

    return query.first()


def _get_processed_data_for_workflow(workflow_id):
    arquivo = _get_latest_file_for_workflow(workflow_id)
    return arquivo, arquivo.dados_extraidos if arquivo else None


def _serialize_balancete_chart(chart: Dashboard) -> Dict[str, Any]:
    options = chart.options or {}
    stored_series = chart.indicators or []
    colors: List[Optional[str]] = chart.colors or []
    series: List[Dict[str, Any]] = []

    for index, serie in enumerate(stored_series):
        value_key = ''
        label = ''

        if isinstance(serie, dict):
            value_key = str(serie.get('value_key') or '').strip()
            label = str(serie.get('label') or '').strip()

        if not label:
            label = value_key or f'Série {index + 1}'

        color = None
        if index < len(colors):
            color_candidate = colors[index]
            if isinstance(color_candidate, str) and color_candidate.strip():
                color = color_candidate.strip()

        if not color and isinstance(options, dict):
            series_colors = options.get('series_colors')
            if isinstance(series_colors, dict):
                color = series_colors.get(value_key)

        series.append({
            'label': label,
            'value_key': value_key,
            'color': color,
        })

    return {
        'id': chart.id,
        'workflow_id': chart.workflow_id,
        'name': chart.nome or 'Gráfico',
        'chart_type': chart.chart_type,
        'label_key': chart.metric,
        'series': series,
        'source_type': 'balancete',
        'source_id': (options or {}).get('source_id', 'latest'),
        'options': options or {},
        'created_at': chart.created_at.isoformat() if chart.created_at else None,
        'updated_at': chart.updated_at.isoformat() if chart.updated_at else None,
    }


def _serialize_analise_chart(chart: AnaliseJPChart) -> Dict[str, Any]:
    options = chart.options or {}
    stored_series = chart.value_fields or []
    series: List[Dict[str, Any]] = []

    for index, serie in enumerate(stored_series):
        if isinstance(serie, dict):
            value_key = str(serie.get('value_key') or '').strip()
            label = str(serie.get('label') or '').strip()
        else:
            value_key = str(serie or '')
            label = value_key

        if not label:
            label = value_key or f'Série {index + 1}'

        color = None
        if isinstance(options, dict):
            series_colors = options.get('series_colors')
            if isinstance(series_colors, dict):
                color = series_colors.get(value_key)

        series.append({
            'label': label,
            'value_key': value_key,
            'color': color,
        })

    return {
        'id': chart.id,
        'workflow_id': chart.workflow_id,
        'name': chart.nome,
        'chart_type': chart.chart_type,
        'label_key': chart.dimension_field,
        'series': series,
        'source_type': 'analise_jp',
        'source_id': chart.categoria,
        'options': options or {},
        'created_at': chart.created_at.isoformat() if chart.created_at else None,
        'updated_at': chart.updated_at.isoformat() if chart.updated_at else None,
    }


def _normalize_color(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str):
        return None
    color = value.strip()
    if not color:
        return None
    if not color.startswith('#'):
        return color
    if len(color) not in {4, 7}:
        return color
    return color


def _extract_series_payload(raw_series: Any) -> List[Dict[str, str]]:
    parsed_series: List[Dict[str, str]] = []
    if not isinstance(raw_series, list):
        return parsed_series

    for item in raw_series:
        if not isinstance(item, dict):
            continue
        value_key = str(item.get('value_key') or '').strip()
        label = str(item.get('label') or '').strip()
        color = _normalize_color(item.get('color'))

        if not value_key:
            continue

        parsed_series.append({
            'value_key': value_key,
            'label': label or value_key,
            'color': color,
        })
    return parsed_series


def _validate_chart_payload(payload: Dict[str, Any]) -> Optional[str]:
    chart_type = str(payload.get('chart_type') or '').strip().lower()
    if chart_type not in ALLOWED_CHART_TYPES:
        return 'Tipo de gráfico inválido.'

    name = str(payload.get('name') or '').strip()
    if not name:
        return 'Informe um nome para o gráfico.'

    label_key = str(payload.get('label_key') or '').strip()
    if not label_key:
        return 'Selecione a coluna de rótulos.'

    series = _extract_series_payload(payload.get('series'))
    if not series:
        return 'Adicione ao menos uma série.'

    if chart_type == 'pie' and len(series) > 1:
        return 'Gráficos de pizza suportam apenas uma série.'

    return None




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
    if workflow.tipo == 'analise_jp':
        context = build_analise_jp_charts_context(workflow)
        return render_template('analise_jp_charts.html', **context)
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
        context = build_analise_jp_dashboard_context(workflow)
        return render_template('analise_jp.html', **context)

    arquivo_atual = _get_latest_file_for_workflow(workflow.id, include_payload=False)

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
        processed_data=None,
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


def _build_series_payload(series: List[Dict[str, str]]) -> Dict[str, Any]:
    indicators: List[Dict[str, str]] = []
    colors: List[Optional[str]] = []
    for serie in series:
        indicators.append({
            'value_key': serie['value_key'],
            'label': serie['label'],
        })
        colors.append(serie.get('color'))
    options = {
        'series_colors': {
            serie['value_key']: serie.get('color')
            for serie in series
            if serie.get('color')
        }
    }
    return {
        'indicators': indicators,
        'colors': colors,
        'options': options,
    }


def _apply_chart_common_options(options: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    final_options = dict(options)
    orientation = payload.get('orientation')
    if orientation == 'horizontal':
        final_options['orientation'] = 'horizontal'
    if payload.get('stacked'):
        final_options['stacked'] = True
    if payload.get('fill_mode'):
        final_options['fill_mode'] = payload.get('fill_mode')
    tension = payload.get('tension')
    if isinstance(tension, (int, float)):
        final_options['tension'] = float(tension)
    return final_options


def _infer_balancete_dataset(processed_data: Dict[str, Any]) -> Dict[str, Any]:
    indicadores = []
    if isinstance(processed_data, dict):
        indicadores = processed_data.get('indicadores') or []

    records: List[Dict[str, Any]] = []
    for indicador in indicadores:
        if isinstance(indicador, dict):
            records.append(indicador)

    label_fields = []
    if records:
        example = records[0]
        label_fields = [key for key in example.keys() if key.startswith('indicador') or key.endswith('nome')]
        if not label_fields and 'indicador' in example:
            label_fields.append('indicador')
        if not label_fields:
            label_fields = [next(iter(example.keys()))]

    numeric_fields: List[Dict[str, str]] = []
    if records:
        candidate_keys = set(records[0].keys())
        for record in records[1:10]:
            candidate_keys.update(record.keys())

        for key in candidate_keys:
            is_numeric = False
            for record in records:
                value = record.get(key)
                if value in (None, ''):
                    continue
                try:
                    float(value)
                    is_numeric = True
                    break
                except (TypeError, ValueError):
                    is_numeric = False
                    break

            if is_numeric:
                numeric_fields.append({'key': key, 'label': _slug_to_label(key)})

    return {
        'records': records,
        'label_fields': label_fields,
        'value_fields': numeric_fields,
        'meta': {
            'periodo_1_label': processed_data.get('periodo_1_label'),
            'periodo_2_label': processed_data.get('periodo_2_label'),
        }
    }


@workflow_bp.route('/api/workflows/<int:workflow_id>/dataset', methods=['GET'])
@login_required
def get_workflow_dataset(workflow_id: int):
    workflow = _get_workflow_for_user(workflow_id)
    if workflow.tipo != 'balancete':
        return jsonify({'error': 'Workflow não é do tipo balancete.'}), 400

    arquivo, processed_data = _get_processed_data_for_workflow(workflow.id)
    if not processed_data:
        return jsonify({'records': [], 'label_fields': [], 'value_fields': [], 'meta': {}, 'arquivo': None})

    dataset = _infer_balancete_dataset(processed_data)

    return jsonify({
        'records': dataset['records'],
        'label_fields': dataset['label_fields'],
        'value_fields': dataset['value_fields'],
        'meta': dataset['meta'],
        'arquivo': _serialize_arquivo_metadata(arquivo) if arquivo else None,
    })


@workflow_bp.route('/api/workflows/<int:workflow_id>/charts', methods=['GET'])
@login_required
def list_workflow_charts(workflow_id: int):
    workflow = _get_workflow_for_user(workflow_id)

    if workflow.tipo == 'balancete':
        charts = (
            Dashboard.query
            .filter_by(workflow_id=workflow.id)
            .order_by(Dashboard.created_at.asc())
            .all()
        )
        serialized = [_serialize_balancete_chart(chart) for chart in charts]
    else:
        charts = (
            AnaliseJPChart.query
            .filter_by(workflow_id=workflow.id)
            .order_by(AnaliseJPChart.created_at.asc())
            .all()
        )
        serialized = [_serialize_analise_chart(chart) for chart in charts]

    return jsonify({'charts': serialized})


@workflow_bp.route('/api/workflows/<int:workflow_id>/charts', methods=['POST'])
@login_required
def create_workflow_chart(workflow_id: int):
    workflow = _get_workflow_for_user(workflow_id)
    payload = request.get_json() or {}

    error = _validate_chart_payload(payload)
    if error:
        return jsonify({'error': error}), 400

    series = _extract_series_payload(payload.get('series'))
    common_options = _build_series_payload(series)
    options = _apply_chart_common_options(common_options['options'], payload)

    if workflow.tipo == 'balancete':
        chart = Dashboard(
            workflow_id=workflow.id,
            nome=payload.get('name', 'Gráfico'),
            chart_type=payload.get('chart_type'),
            metric=payload.get('label_key'),
            indicators=common_options['indicators'],
            colors=common_options['colors'],
            options={
                **options,
                'source_type': 'balancete',
                'source_id': payload.get('source_id', 'latest'),
            },
        )
    else:
        categoria = str(payload.get('source_id') or '').strip()
        try:
            _validate_category(categoria)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400

        chart = AnaliseJPChart(
            workflow_id=workflow.id,
            categoria=categoria,
            nome=payload.get('name', 'Gráfico'),
            chart_type=payload.get('chart_type'),
            dimension_field=payload.get('label_key'),
            value_fields=common_options['indicators'],
            options={
                **options,
                'source_type': 'analise_jp',
            },
        )

    db.session.add(chart)
    db.session.commit()

    serialized = (
        _serialize_balancete_chart(chart)
        if workflow.tipo == 'balancete'
        else _serialize_analise_chart(chart)
    )

    return jsonify({'message': 'Gráfico criado com sucesso.', 'chart': serialized}), 201


def _get_chart_for_workflow(workflow: Workflow, chart_id: int):
    if workflow.tipo == 'balancete':
        return Dashboard.query.filter_by(id=chart_id, workflow_id=workflow.id).first_or_404()
    return AnaliseJPChart.query.filter_by(id=chart_id, workflow_id=workflow.id).first_or_404()


@workflow_bp.route('/api/workflows/<int:workflow_id>/charts/<int:chart_id>', methods=['PUT'])
@login_required
def update_workflow_chart(workflow_id: int, chart_id: int):
    workflow = _get_workflow_for_user(workflow_id)
    chart = _get_chart_for_workflow(workflow, chart_id)
    payload = request.get_json() or {}

    error = _validate_chart_payload(payload)
    if error:
        return jsonify({'error': error}), 400

    series = _extract_series_payload(payload.get('series'))
    common_options = _build_series_payload(series)
    options = _apply_chart_common_options(common_options['options'], payload)

    chart.nome = payload.get('name', chart.nome)
    chart.chart_type = payload.get('chart_type', chart.chart_type)

    if workflow.tipo == 'balancete':
        chart.metric = payload.get('label_key', chart.metric)
        chart.indicators = common_options['indicators']
        chart.colors = common_options['colors']
        merged_options = {
            **options,
            'source_type': 'balancete',
            'source_id': payload.get('source_id', 'latest'),
        }
        chart.options = merged_options
    else:
        categoria = str(payload.get('source_id') or chart.categoria).strip()
        try:
            _validate_category(categoria)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400

        chart.categoria = categoria
        chart.dimension_field = payload.get('label_key', chart.dimension_field)
        chart.value_fields = common_options['indicators']
        chart.options = {
            **options,
            'source_type': 'analise_jp',
        }

    db.session.commit()

    serialized = (
        _serialize_balancete_chart(chart)
        if workflow.tipo == 'balancete'
        else _serialize_analise_chart(chart)
    )

    return jsonify({'message': 'Gráfico atualizado com sucesso.', 'chart': serialized})


@workflow_bp.route('/api/workflows/<int:workflow_id>/charts/<int:chart_id>', methods=['DELETE'])
@login_required
def delete_workflow_chart(workflow_id: int, chart_id: int):
    workflow = _get_workflow_for_user(workflow_id)
    chart = _get_chart_for_workflow(workflow, chart_id)

    db.session.delete(chart)
    db.session.commit()

    return jsonify({'message': 'Gráfico removido com sucesso.'})


@workflow_bp.route('/api/workflows/<int:workflow_id>/charts/<int:chart_id>/duplicate', methods=['POST'])
@login_required
def duplicate_workflow_chart(workflow_id: int, chart_id: int):
    workflow = _get_workflow_for_user(workflow_id)
    chart = _get_chart_for_workflow(workflow, chart_id)

    if workflow.tipo == 'balancete':
        duplicated = Dashboard(
            workflow_id=workflow.id,
            nome=f"{chart.nome} (cópia)",
            chart_type=chart.chart_type,
            metric=chart.metric,
            indicators=list(chart.indicators or []),
            colors=list(chart.colors or []),
            options=dict(chart.options or {}),
        )
    else:
        duplicated = AnaliseJPChart(
            workflow_id=workflow.id,
            categoria=chart.categoria,
            nome=f"{chart.nome} (cópia)",
            chart_type=chart.chart_type,
            dimension_field=chart.dimension_field,
            value_fields=list(chart.value_fields or []),
            options=dict(chart.options or {}),
        )

    db.session.add(duplicated)
    db.session.commit()

    serialized = (
        _serialize_balancete_chart(duplicated)
        if workflow.tipo == 'balancete'
        else _serialize_analise_chart(duplicated)
    )

    return jsonify({'message': 'Gráfico duplicado com sucesso.', 'chart': serialized}), 201
