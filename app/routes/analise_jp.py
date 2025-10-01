import io
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

import pandas as pd
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app import db
from app.models.analise_upload import AnaliseUpload
from app.models.analise_jp_chart import AnaliseJPChart
from app.models.workflow import Workflow
from app.services.theme_service import get_theme_context


analise_jp_bp = Blueprint('analise_jp', __name__)

ANALISE_JP_CATEGORIES: List[str] = [
    'simples_nacional',
    'lucro_real',
    'banco_horas',
    'notas',
    'lucro_presumido',
    'departamento_pessoal',
    'colaboradores',
    'impostos_fiscal',
    'empresas_mes',
    'servicos_simples',
    'servicos_lucro_presumido',
    'servicos_contabil',
    'servicos_contabil_det',
]

ALLOWED_EXTENSIONS = {'.csv', '.xlsx'}

ANALISE_JP_ALLOWED_CHART_TYPES = {
    'bar', 'line', 'pie', 'doughnut', 'radar'
}


def _get_workflow_or_404(workflow_id: int) -> Workflow:
    return Workflow.query.filter_by(id=workflow_id, usuario_id=current_user.id).first_or_404()


def _validate_category(categoria: str) -> None:
    if categoria not in ANALISE_JP_CATEGORIES:
        raise ValueError('Categoria invalida.')


def _slug_to_label(slug: str) -> str:
    parts = [part.capitalize() for part in slug.split('_') if part]
    return ' '.join(parts) if parts else slug


def _get_latest_upload_for_category(workflow_id: int, categoria: str) -> Optional[AnaliseUpload]:
    return (
        AnaliseUpload.query
        .filter_by(workflow_id=workflow_id, categoria=categoria)
        .order_by(AnaliseUpload.created_at.desc())
        .first()
    )


def _decode_csv_bytes(data: bytes) -> io.StringIO:
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = data.decode('latin-1')
    return io.StringIO(text)


def _load_dataframe(file_bytes: bytes, extension: str) -> pd.DataFrame:
    """
    Load the uploaded file into a dataframe preserving the original textual values.

    When pandas infers numeric types automatically, numbers such as 0.1034 can end up
    represented as 0.10339999999999999 due to floating point precision. For these
    uploads the goal is to keep the exact content provided in the CSV/XLSX templates
    so the data shown in the UI matches the spreadsheet. Reading everything as
    strings avoids unwanted conversions while still letting us normalise empty
    values later in the pipeline.
    """

    if extension == '.csv':
        buffer = _decode_csv_bytes(file_bytes)
        dataframe = pd.read_csv(
            buffer,
            sep=None,
            engine='python',
            dtype=str,
            keep_default_na=False,
        )
    else:
        buffer = io.BytesIO(file_bytes)
        dataframe = pd.read_excel(
            buffer,
            engine='openpyxl',
            dtype=str,
            na_filter=False,
        )

    dataframe = dataframe.dropna(how='all')
    return dataframe


def _dataframe_to_records(dataframe: pd.DataFrame) -> List[dict]:
    if dataframe.empty:
        raise ValueError('Arquivo sem dados para processar.')

    normalized_columns = []
    for idx, column in enumerate(dataframe.columns, start=1):
        header = str(column).strip()
        if not header:
            header = f'Coluna {idx}'
        normalized_columns.append(header)
    dataframe.columns = normalized_columns

    dataframe = dataframe.fillna('')
    records: List[dict] = []
    for _, row in dataframe.iterrows():
        if all(str(value).strip() == '' for value in row.values):
            continue
        record = {}
        for column in dataframe.columns:
            value = row[column]

            if value is None:
                cleaned_value = ''
            else:
                value_str = str(value)
                cleaned_value = value_str.strip()

            record[column] = cleaned_value
        records.append(record)

    if not records:
        raise ValueError('Nenhum dado valido encontrado no arquivo enviado.')

    return records


def _extract_payload(file: FileStorage) -> Tuple[List[dict], bytes]:
    filename = file.filename or ''
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError('Formato invalido. Utilize arquivos CSV ou XLSX.')

    file.stream.seek(0)
    file_bytes = file.stream.read()
    if not file_bytes:
        raise ValueError('Arquivo vazio.')

    dataframe = _load_dataframe(file_bytes, extension)
    records = _dataframe_to_records(dataframe)

    return records, file_bytes


@analise_jp_bp.route('/analise_jp/<int:workflow_id>')
@login_required
def analise_jp_view(workflow_id: int):
    workflow = _get_workflow_or_404(workflow_id)
    if workflow.tipo != 'analise_jp':
        return redirect(url_for('workflow.workflow_view', workflow_nome=workflow.nome))

    theme = get_theme_context()
    return render_template(
        'analise_jp.html',
        workflow=workflow,
        theme=theme,
        categories=ANALISE_JP_CATEGORIES
    )


@analise_jp_bp.route('/analise_jp/<int:workflow_id>/graficos')
@login_required
def analise_jp_charts_view(workflow_id: int):
    workflow = _get_workflow_or_404(workflow_id)
    if workflow.tipo != 'analise_jp':
        return redirect(url_for('workflow.workflow_view', workflow_nome=workflow.nome))

    theme = get_theme_context()

    categories_meta = []
    for categoria in ANALISE_JP_CATEGORIES:
        latest_upload = _get_latest_upload_for_category(workflow.id, categoria)
        categories_meta.append({
            'slug': categoria,
            'label': _slug_to_label(categoria),
            'has_data': bool(latest_upload and latest_upload.dados_extraidos),
            'latest_upload': None if not latest_upload else {
                'id': latest_upload.id,
                'nome_arquivo': latest_upload.nome_arquivo,
                'created_at': latest_upload.created_at.isoformat() if latest_upload.created_at else None
            }
        })

    charts = (
        AnaliseJPChart.query
        .filter_by(workflow_id=workflow.id)
        .order_by(AnaliseJPChart.created_at.desc())
        .all()
    )

    return render_template(
        'analise_jp_charts.html',
        workflow=workflow,
        theme=theme,
        categories_meta=categories_meta,
        allowed_chart_types=sorted(ANALISE_JP_ALLOWED_CHART_TYPES),
        charts=[chart.to_dict() for chart in charts]
    )


@analise_jp_bp.route('/analise_jp/<int:workflow_id>/uploads/<string:categoria>', methods=['GET'])
@login_required
def listar_uploads(workflow_id: int, categoria: str):
    workflow = _get_workflow_or_404(workflow_id)
    try:
        _validate_category(categoria)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    uploads = (
        AnaliseUpload.query
        .filter_by(workflow_id=workflow.id, categoria=categoria)
        .order_by(AnaliseUpload.created_at.desc())
        .all()
    )

    return jsonify({'uploads': [upload.to_dict() for upload in uploads]})


@analise_jp_bp.route('/analise_jp/<int:workflow_id>/api/categorias/<string:categoria>/dataset', methods=['GET'])
@login_required
def obter_dataset_categoria(workflow_id: int, categoria: str):
    workflow = _get_workflow_or_404(workflow_id)
    try:
        _validate_category(categoria)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    upload = _get_latest_upload_for_category(workflow.id, categoria)
    if not upload or not upload.dados_extraidos:
        return jsonify({'error': 'Nenhum upload encontrado para a categoria selecionada.'}), 404

    records = upload.dados_extraidos if isinstance(upload.dados_extraidos, list) else []
    fields: List[str] = []
    for record in records:
        if isinstance(record, dict):
            fields = list(record.keys())
            break

    return jsonify({
        'categoria': categoria,
        'categoria_label': _slug_to_label(categoria),
        'record_count': len(records),
        'fields': fields,
        'records': records,
        'upload': {
            'id': upload.id,
            'nome_arquivo': upload.nome_arquivo,
            'created_at': upload.created_at.isoformat() if upload.created_at else None
        }
    })


@analise_jp_bp.route('/analise_jp/<int:workflow_id>/upload/<string:categoria>', methods=['POST'])
@login_required
def upload_categoria(workflow_id: int, categoria: str):
    workflow = _get_workflow_or_404(workflow_id)
    if workflow.tipo != 'analise_jp':
        return jsonify({'error': 'Workflow nao suporta uploads de analise_jp.'}), 400

    try:
        _validate_category(categoria)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    arquivo = request.files.get('arquivo')
    if not arquivo or not arquivo.filename:
        return jsonify({'error': 'Nenhum arquivo foi enviado.'}), 400

    try:
        registros, file_bytes = _extract_payload(arquivo)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception:
        return jsonify({'error': 'Falha ao processar o arquivo enviado.'}), 500

    safe_name = secure_filename(arquivo.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    stored_name = f"{workflow_id}_{categoria}_{timestamp}_{safe_name}"

    upload_root = Path(current_app.config['UPLOAD_FOLDER'])
    destination = AnaliseUpload.build_storage_path(upload_root, workflow_id, categoria, stored_name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(file_bytes)

    upload = AnaliseUpload(
        workflow_id=workflow.id,
        categoria=categoria,
        nome_arquivo=safe_name,
        caminho_arquivo=str(destination),
        dados_extraidos=registros
    )

    db.session.add(upload)
    db.session.commit()

    return jsonify({'message': 'Upload realizado com sucesso!', 'upload': upload.to_dict()}), 201


@analise_jp_bp.route(
    '/analise_jp/<int:workflow_id>/uploads/<string:categoria>/<int:upload_id>',
    methods=['DELETE']
)
@login_required
def excluir_upload(workflow_id: int, categoria: str, upload_id: int):
    workflow = _get_workflow_or_404(workflow_id)
    if workflow.tipo != 'analise_jp':
        return jsonify({'error': 'Workflow nao suporta exclusao de uploads de analise_jp.'}), 400

    try:
        _validate_category(categoria)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    upload = (
        AnaliseUpload.query
        .filter_by(id=upload_id, workflow_id=workflow.id, categoria=categoria)
        .first()
    )

    if not upload:
        return jsonify({'error': 'Upload nao encontrado.'}), 404

    file_path = Path(upload.caminho_arquivo)
    try:
        if file_path.exists():
            file_path.unlink()
    except OSError:
        current_app.logger.exception('Falha ao remover arquivo do upload %s', upload_id)
        return jsonify({'error': 'Nao foi possivel remover o arquivo associado ao upload.'}), 500

    db.session.delete(upload)
    db.session.commit()

    return jsonify({'message': 'Upload removido com sucesso.'}), 200


@analise_jp_bp.route('/analise_jp/<int:workflow_id>/api/graficos', methods=['GET'])
@login_required
def listar_graficos_analise_jp(workflow_id: int):
    workflow = _get_workflow_or_404(workflow_id)
    charts = (
        AnaliseJPChart.query
        .filter_by(workflow_id=workflow.id)
        .order_by(AnaliseJPChart.created_at.desc())
        .all()
    )

    return jsonify([chart.to_dict() for chart in charts])


@analise_jp_bp.route('/analise_jp/<int:workflow_id>/api/graficos', methods=['POST'])
@login_required
def criar_grafico_analise_jp(workflow_id: int):
    workflow = _get_workflow_or_404(workflow_id)
    if workflow.tipo != 'analise_jp':
        return jsonify({'error': 'Workflow nao suporta graficos para este tipo.'}), 400

    payload = request.get_json() or {}

    categoria = (payload.get('categoria') or '').strip()
    if not categoria:
        return jsonify({'error': 'Categoria obrigatoria.'}), 400
    try:
        _validate_category(categoria)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    chart_type = (payload.get('chart_type') or '').strip().lower()
    if chart_type not in ANALISE_JP_ALLOWED_CHART_TYPES:
        return jsonify({'error': 'Tipo de grafico invalido.'}), 400

    dimension_field = (payload.get('dimension_field') or '').strip()
    if not dimension_field:
        return jsonify({'error': 'Selecione um campo para o eixo principal.'}), 400

    raw_values = payload.get('value_fields') or payload.get('series') or []
    if isinstance(raw_values, str):
        raw_values = [raw_values]
    value_fields: List[str] = []
    for item in raw_values:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned and cleaned not in value_fields:
                value_fields.append(cleaned)

    if not value_fields:
        return jsonify({'error': 'Selecione ao menos um campo de valor.'}), 400

    upload = _get_latest_upload_for_category(workflow.id, categoria)
    if not upload or not upload.dados_extraidos:
        return jsonify({'error': 'Nenhum dado disponivel para a categoria selecionada.'}), 400

    records = upload.dados_extraidos if isinstance(upload.dados_extraidos, list) else []
    if not records:
        return jsonify({'error': 'Nenhum dado processado encontrado para a categoria.'}), 400

    available_fields = set()
    for record in records:
        if isinstance(record, dict):
            available_fields.update(record.keys())

    if dimension_field not in available_fields:
        return jsonify({'error': 'Campo de eixo invalido para a categoria selecionada.'}), 400

    missing_fields = [field for field in value_fields if field not in available_fields]
    if missing_fields:
        return jsonify({'error': f"Campos nao encontrados na base: {', '.join(missing_fields)}"}), 400

    nome = (payload.get('nome') or payload.get('title') or '').strip()
    if not nome:
        nome = f"{_slug_to_label(categoria)} - {chart_type.title()}"

    options = payload.get('options') or {}
    if not isinstance(options, dict):
        options = {}

    colors = payload.get('colors') or []
    if isinstance(colors, list):
        cleaned_colors = [
            color.strip() for color in colors
            if isinstance(color, str) and color.strip()
        ]
        if cleaned_colors:
            options['colors'] = cleaned_colors

    novo_grafico = AnaliseJPChart(
        workflow_id=workflow.id,
        categoria=categoria,
        nome=nome,
        chart_type=chart_type,
        dimension_field=dimension_field,
        value_fields=value_fields,
        options=options
    )

    try:
        db.session.add(novo_grafico)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Nao foi possivel salvar o grafico.'}), 500

    return jsonify({
        'message': 'Grafico criado com sucesso.',
        'grafico': novo_grafico.to_dict()
    }), 201


@analise_jp_bp.route('/analise_jp/<int:workflow_id>/api/graficos/<int:grafico_id>', methods=['DELETE'])
@login_required
def excluir_grafico_analise_jp(workflow_id: int, grafico_id: int):
    workflow = _get_workflow_or_404(workflow_id)

    grafico = (
        AnaliseJPChart.query
        .filter_by(id=grafico_id, workflow_id=workflow.id)
        .first()
    )

    if not grafico:
        return jsonify({'error': 'Grafico nao encontrado.'}), 404

    try:
        db.session.delete(grafico)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Nao foi possivel remover o grafico.'}), 500

    return jsonify({'message': 'Grafico removido com sucesso.'})
